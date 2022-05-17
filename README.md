# crowsnest-processor-opendlv-radar

A processing microservice within the crowsnest ecosystem which listens on `RadarDetectionReading`s from an OpenDLV session and converts and outputs these as "single level point clouds" with weights.


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