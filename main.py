"""Main entrypoint for this application"""
from datetime import datetime, timezone
from functools import lru_cache
from typing import Tuple
import logging
import warnings

import numpy as np
from environs import Env
from streamz import Stream
from paho.mqtt.client import Client as MQTT

from pycluon import OD4Session, Envelope as cEnvelope
from pycluon.importer import import_odvd
from brefv.envelope import Envelope

# Reading config from environment variables
env = Env()

MQTT_BROKER_HOST = env("MQTT_BROKER_HOST")
MQTT_BROKER_PORT = env.int("MQTT_BROKER_PORT", 1883)
MQTT_CLIENT_ID = env("MQTT_CLIENT_ID", None)
MQTT_TRANSPORT = env("MQTT_TRANSPORT", "tcp")
MQTT_TLS = env.bool("MQTT_TLS", False)
MQTT_USER = env("MQTT_USER", None)
MQTT_PASSWORD = env("MQTT_PASSWORD", None)
MQTT_BASE_TOPIC = env("MQTT_BASE_TOPIC")

CLUON_CID = env.int("CLUON_CID", 111)
CLUON_MSG_ID = env.int("CLUON_MS_ID", 1201)

RADAR_ATTITUDE: list = env.list("RADAR_ATTITUDE", [0, 0, 0], subcast=float, validate=lambda x: len(x) == 3)
RADAR_MIN_READING_WEIGHT = env.int("RADAR_MIN_READING_WEIGHT", 0)
RADAR_SWEEP_ANGULAR_SUBSETTING = env.int("RADAR_SWEEP_ANGULAR_SUBSETTING", 10)
RADAR_SWEEP_RADIAL_SUBSETTING = env.int("RADAR_SWEEP_RADIAL_SUBSETTING", 2)

LOG_LEVEL = env.log_level("LOG_LEVEL", logging.DEBUG)

## Import and generate code for message specifications
radar_message_spec = import_odvd("radar.odvd")

# Setup logger
logging.basicConfig(level=LOG_LEVEL)
logging.captureWarnings(True)
warnings.filterwarnings("once")
LOGGER = logging.getLogger("crowsnest-processor-opendlv-radar")

# Create mqtt client and confiure it according to configuration
mq = MQTT(client_id=MQTT_CLIENT_ID, transport=MQTT_TRANSPORT)
mq.username_pw_set(MQTT_USER, MQTT_PASSWORD)
if MQTT_TLS:
    mq.tls_set()


# Not empty filter
not_empty = lambda x: x is not None


### Helper functions


@lru_cache
def decode_azimuth(spoke_direction: int) -> float:
    """Decode azimuth from integer spoke_direction"""
    return spoke_direction / 4096 * 360


@lru_cache
def decode_distances(spoke_length: int, _range: float) -> np.ndarray:
    """Decode distances from spoke length and range metadata"""
    return np.array(range(spoke_length)) * _range / spoke_length


### Processing functions


def unpack_spoke(envelope: cEnvelope) -> Tuple[float, np.ndarray, np.ndarray]:
    """Extract a radar message from the cluon envelope"""
    LOGGER.info("Got envelope from pycluon")
    try:
        radar_message = radar_message_spec.opendlv_proxy_RadarDetectionReading()
        radar_message.ParseFromString(envelope.serialized_data)

        str_id = str(envelope.sender_stamp)
        # str_time = str(envelope.sender_timestamp)

        LOGGER.info("Sender ID: %s", str_id)
        
        

        # Unpack message
        azimuth = decode_azimuth(int(radar_message.azimuth))
        radar_range = radar_message.range
        spoke_data = np.frombuffer(radar_message.data, dtype=np.uint8)

        LOGGER.debug(
            "Radar message unpacked with azimuth: %.4f, range: %.4f and spoke length: %d",
            azimuth,
            radar_range,
            len(spoke_data),
        )

        distances = decode_distances(len(spoke_data), radar_range)

        # Radial filtering
        distances = distances[::RADAR_SWEEP_RADIAL_SUBSETTING]
        spoke_data = spoke_data[::RADAR_SWEEP_RADIAL_SUBSETTING]

        # Minimum weight filtering
        mask = spoke_data > RADAR_MIN_READING_WEIGHT
        distances = distances[mask]
        spoke_data = spoke_data[mask]

        return (
            azimuth,
            distances,
            spoke_data,
        )

    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Exception when unpacking a radar message")
        return None


def polar_to_cartesian(azimuth: float, distances: np.ndarray, weights: np.ndarray) -> Tuple[float, np.ndarray]:
    """Map from polar to cartesian coordinates"""
    LOGGER.debug("Converting to cartesian for azimuth: %.4f", azimuth)

    x = distances * np.cos(np.deg2rad(azimuth))  # pylint: disable=invalid-name
    y = distances * np.sin(np.deg2rad(azimuth))  # pylint: disable=invalid-name

    # Distance correction (Do not know why...)
    x = x * 1.852
    y = y * 1.852

    points = np.column_stack((y, x))

    return azimuth, points, weights


# Simple "buffering" to output full rotations instead of each individual spoke
# pylint: disable=invalid-name
sweep_points = []
sweep_weights = []
last_azimuth = -1


def buffer_to_full_360_view(azimuth: float, points: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Buffer until we have a full sweep, then emit"""

    global sweep_points, sweep_weights, last_azimuth  # pylint: disable=global-statement

    out = None

    if azimuth < last_azimuth:
        # We just started a new rotation, emit the previous one

        # Angular filtering
        sweep_points = sweep_points[::RADAR_SWEEP_ANGULAR_SUBSETTING]
        sweep_weights = sweep_weights[::RADAR_SWEEP_ANGULAR_SUBSETTING]

        # Update out
        out = (
            np.concatenate(sweep_points, axis=0),
            np.concatenate(sweep_weights, axis=0),
        )

        # Clear the buffers
        sweep_points.clear()
        sweep_weights.clear()
        LOGGER.info("Emitting new sweep!")

    # Add the current spoke
    last_azimuth = azimuth
    sweep_points.append(points)
    sweep_weights.append(weights)

    LOGGER.debug("Buffering azimuth %.4f", azimuth)

    return out


def to_brefv(points: np.ndarray, weights: np.ndarray) -> Envelope:
    """To brefv envelope"""

    LOGGER.info("Assembling new brefv envelope")

    envelope = Envelope(
        sent_at=datetime.now(timezone.utc).isoformat(),
        message={
            "points": points.tolist(),
            "weights": weights.tolist(),
        },
    )

    return envelope


def to_mqtt(envelope: Envelope):
    """Publish an envelope to a mqtt topic"""

    topic = f"{MQTT_BASE_TOPIC}"

    payload = envelope.json()

    LOGGER.debug("Publishing on %s with payload size: %s", topic, len(payload.encode()))
    try:
        mq.publish(
            topic,
            payload,
        )
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Failed publishing to broker!")


if __name__ == "__main__":

    # Setup pipeline
    source = Stream()

    pipe = (
        source.map(unpack_spoke)
        .filter(not_empty)
        .latest()  # Drop anything we dont manage to process...
        .starmap(polar_to_cartesian)
        .starmap(buffer_to_full_360_view)
        .filter(not_empty)
        .starmap(to_brefv)
        .sink(to_mqtt)
    )

    # Connect to broker
    LOGGER.info("Connecting to MQTT broker %s %d", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    mq.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)

    LOGGER.info("All setup done, lets start processing messages!")

    # Register triggers
    session = OD4Session(CLUON_CID)
    session.add_data_trigger(CLUON_MSG_ID, source.emit)

    mq.loop_forever()
