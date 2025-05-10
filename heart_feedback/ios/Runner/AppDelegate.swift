import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate {
    let recorder = VideoRecorder.shared

    override func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        GeneratedPluginRegistrant.register(with: self)

        let controller = window?.rootViewController as! FlutterViewController
        let methodChannel = FlutterMethodChannel(name: "video_recorder", binaryMessenger: controller.binaryMessenger)

        recorder.initialize(channel: methodChannel)

        methodChannel.setMethodCallHandler { (call, result) in
            if call.method == "startRecording" {
                self.recorder.startRecording()
                result(nil)
            } else if call.method == "stopRecording" {
                self.recorder.stopRecording()
                result(nil)
            } else {
                result(FlutterMethodNotImplemented)
            }
        }

        return super.application(application, didFinishLaunchingWithOptions: launchOptions)
    }
}
