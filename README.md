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