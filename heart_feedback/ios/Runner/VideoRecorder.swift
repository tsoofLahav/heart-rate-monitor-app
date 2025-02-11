import AVFoundation
import Flutter

class VideoRecorder: NSObject {
    static let shared = VideoRecorder()
    private var captureSession: AVCaptureSession?
    private var movieOutput = AVCaptureMovieFileOutput()
    private var isRecording = false
    private var methodChannel: FlutterMethodChannel?

    func initialize(channel: FlutterMethodChannel) {
        self.methodChannel = channel
        setupSession()
    }

    private func setupSession() {
        captureSession = AVCaptureSession()
        captureSession?.sessionPreset = .medium

        guard let videoDevice = AVCaptureDevice.default(for: .video),
              let audioDevice = AVCaptureDevice.default(for: .audio),
              let videoInput = try? AVCaptureDeviceInput(device: videoDevice),
              let audioInput = try? AVCaptureDeviceInput(device: audioDevice) else {
            print("Failed to get camera or microphone")
            return
        }

        if captureSession!.canAddInput(videoInput) { captureSession!.addInput(videoInput) }
        if captureSession!.canAddInput(audioInput) { captureSession!.addInput(audioInput) }
        if captureSession!.canAddOutput(movieOutput) { captureSession!.addOutput(movieOutput) }

        DispatchQueue.global(qos: .background).async {
            self.captureSession?.startRunning()
        }
    }

    func startRecording() {
        if isRecording { return }
        isRecording = true

        // Enable Flash (Torch Mode)
        if let videoDevice = AVCaptureDevice.default(for: .video), videoDevice.hasTorch {
            do {
                try videoDevice.lockForConfiguration()
                videoDevice.torchMode = .on
                videoDevice.unlockForConfiguration()
            } catch {
                print("Torch could not be used: \(error.localizedDescription)")
            }
        }

        DispatchQueue.global(qos: .background).async {
            self.recordLoop()
        }
    }


    func stopRecording() {
        if !isRecording { return }
        isRecording = false
        movieOutput.stopRecording()
        captureSession?.stopRunning()

        // Turn Off Flash (Torch Mode)
        if let videoDevice = AVCaptureDevice.default(for: .video), videoDevice.hasTorch {
            do {
                try videoDevice.lockForConfiguration()
                videoDevice.torchMode = .off
                videoDevice.unlockForConfiguration()
            } catch {
                print("Torch could not be turned off: \(error.localizedDescription)")
            }
        }
    }


    private func recordLoop() {
        while isRecording {
            let outputPath = NSTemporaryDirectory() + "video_\(Date().timeIntervalSince1970).mp4"
            let videoURL = URL(fileURLWithPath: outputPath)
            
            movieOutput.startRecording(to: videoURL, recordingDelegate: self)
            Thread.sleep(forTimeInterval: 1.0)  // Record in slices of 1 second
            movieOutput.stopRecording()
        }
    }
}

extension VideoRecorder: AVCaptureFileOutputRecordingDelegate {
    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        if let error = error {
            print("Recording error: \(error.localizedDescription)")
            return
        }
        
        print("Video saved at \(outputFileURL.absoluteString)")
        methodChannel?.invokeMethod("videoSaved", arguments: outputFileURL.absoluteString)
    }
}
