# crowsnest-processor-opendlv-radar

A processing microservice within the crowsnest ecosystem which listens on `RadarDetectionReading`s from an OpenDLV session and converts and outputs these as "single level point clouds" with weights. 

Output minimized example:  
```
{
    "sent_at": "2023-02-14T13:37:38.326046+00:00", 
    "message": 
    {
        "points": [[0.0, 0.0], [2.9296840530811576, 0.0044940825770061485], [5.859368106162315, 0.008988165154012297], ...] 
    }
}
```

## Docker compose example

```yml
  crowsnest-processor-radar-0:
    image: ghcr.io/mo-rise/crowsnest-processor-opendlv-radar:0.1.17
    container_name: cw-radar-processor-0
    restart: unless-stopped
    network_mode: "host"
    deploy:
      resources:
        limits:
          memory: 1024M
    environment:
      - CLUON_CID=65
      - CLUON_ENVELOPE_ID=1201
      - MQTT_BROKER_HOST=localhost
      - MQTT_BROKER_PORT=1883
      - MQTT_BASE_TOPIC=CROWSNEST/SEAHORSE/RADAR/0/SWEEP
      - RADAR_MIN_READING_WEIGHT=0
      - RADAR_SWEEP_ANGULAR_SUBSETTING=4
      - RADAR_SWEEP_RADIAL_SUBSETTING=4
      - RADAR_MAX_UPDATE_FREQUENCY=1
```



## Development setup
To setup the development environment:

    python3 -m venv venv
    source ven/bin/activate

Install everything thats needed for development:

    pip install -r requirements_dev.txt

In addition, code for `brefv` must be generated using the following commands:

    mkdir brefv
    datamodel-codegen --input brefv-spec/envelope.json --input-file-type jsonschema --output brefv/envelope.py
    datamodel-codegen --input brefv-spec/messages --input-file-type jsonschema  --reuse-model --output brefv/messages

To run the linters:

    black main.py tests
    pylint main.py

To run the tests:

    python -m pytest --verbose tests


## License
Apache 2.0, see [LICENSE](./LICENSE)