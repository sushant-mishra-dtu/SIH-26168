# IDR Navigator Android UI

Standalone Android Studio UI prototype for the Smart India Hackathon 26168 demo surface. Copy this `android-ui/` folder into the real repository when the Android seat is ready.

## What is included

- Jetpack Compose operator UI with a vector route map.
- Live position marker and covariance-style uncertainty ellipse.
- GNSS/INS mode, fix status, position, sensor rate, and timestamp jitter panels.
- Foreground service for continuous recording, as required by the source `android/README.md`.
- Uncalibrated accelerometer and gyroscope registration.
- Location updates with explicit runtime permissions and notification channel.
- `DeadReckoningBackend` interface separating UI from the data source.
- Static preview telemetry so the design can be reviewed without permissions, a device, or a
	connected backend.

## Backend handoff

The current app entry point is intentionally UI-only. It uses fixed preview telemetry and does not
request permissions or start the foreground service. The backend and local estimator remain in the
folder for the later integration pass.

## Open Android work

- Replace the illustrative route drawing with OSM/CSR map data when the matcher exists.
- Connect the native filter covariance and pose to the existing telemetry model.
- Add a short backward smoother for tunnel exit multipath fixes.
- Measure sustained 200 Hz thermal and battery behavior on each target phone.

## Open in Android Studio

Open this folder as a project. Android Studio will resolve the Gradle dependencies and run the `app` module. A physical Android device is recommended because sensor and GNSS behavior cannot be meaningfully tested in the emulator.
