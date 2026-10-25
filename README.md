# Temperature Notifier

A daily AWS Lambda that checks the local forecast and sends a Slack message when
batteries should be moved indoors or outdoors.

## Deploy

The project uses AWS SAM and targets Python 3.12. Install the SAM CLI, configure
AWS credentials, then run:

```powershell
sam build
sam deploy --guided
```

The checked-in SAM configuration uses a local build (`use_container = false`),
so Docker is not required for `sam build`.

The template creates an EventBridge Scheduler schedule that invokes the function
once per day at 6:30 AM. It defaults to `America/New_York`, including daylight
saving-time changes.

The Lambda handler is `temperature_notifier.main.lambda_handler`.

## Tests

Install test dependencies and run the isolated unit tests with:

```powershell
python -m pip install -r requirements-dev.txt
pytest
```

The application package lives in `src/temperature_notifier`; deployment
dependencies are in `src/requirements.txt`.
