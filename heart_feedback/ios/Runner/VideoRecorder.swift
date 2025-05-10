import AVFoundation
import Flutter

class VideoRecorder: NSObject {
    static let shared = VideoRecorder()
    
    private var captureSession: AVCaptureSession?
    private var movieOutput = AVCaptureMovieFileOutput()
    private var methodChannel: FlutterMethodChannel?
    private var isRecording = false

    func initialize(channel: FlutterMethodChannel) {
        self.methodChannel = channel
        setupSession()
    }

    /// **Sets up the Camera Session for Background Recording**
    private func setupSession() {
        captureSession = AVCaptureSession()
        captureSession?.sessionPreset = .medium

        guard let videoDevice = AVCaptureDevice.default(for: .video),
              let videoInput = try? AVCaptureDeviceInput(device: videoDevice) else {
            print("[VideoRecorder] ERROR: Could not access camera")
            return
        }

        if captureSession!.canAddInput(videoInput) {
            captureSession!.addInput(videoInput)
        }
        
        if captureSession!.canAddOutput(movieOutput) {
            captureSession!.addOutput(movieOutput)
        }

        DispatchQueue.global(qos: .background).async {
            self.captureSession?.startRunning()
        }
    }

    /// **Starts recording in a loop (Enables Flash)**
    func startRecording() {
        if isRecording { return }
        isRecording = true
        print("[VideoRecorder] Recording started")
        
        toggleFlash(on: true) // 🔦 Keep flash ON while recording loop is active

        DispatchQueue.global(qos: .background).async {
            self.recordLoop()
        }
    }

    /// **Stops recording completely (Disables Flash)**
    func stopRecording() {
        if !isRecording { return }
        isRecording = false
        movieOutput.stopRecording()
        captureSession?.stopRunning()
        
        toggleFlash(on: false) // 🔦 Turn OFF flash when recording fully stops
        print("[VideoRecorder] Recording stopped")
    }

    /// **Handles continuous recording without gaps**
    private func recordLoop() {
        while isRecording {
            let outputPath = NSTemporaryDirectory() + "video_\(Date().timeIntervalSince1970).mp4"
            let videoURL = URL(fileURLWithPath: outputPath)

            if movieOutput.isRecording {
                movieOutput.stopRecording()
                Thread.sleep(forTimeInterval: 0.1) // Ensure a short delay before restarting
            }

            movieOutput.startRecording(to: videoURL, recordingDelegate: self)
            Thread.sleep(forTimeInterval: 1.0)  // Record each video in 1-second slices
        }
    }

    /// **Toggles Flashlight On/Off**
    private func toggleFlash(on: Bool) {
        guard let videoDevice = AVCaptureDevice.default(for: .video), videoDevice.hasTorch else {
            print("[VideoRecorder] Flash not available")
            return
        }

        do {
            try videoDevice.lockForConfiguration()
            videoDevice.torchMode = on ? .on : .off
            videoDevice.unlockForConfiguration()
            print("[VideoRecorder] Flash \(on ? "enabled" : "disabled")")
        } catch {
            print("[VideoRecorder] ERROR: Could not toggle flash - \(error.localizedDescription)")
        }
    }
}

/// **Delegate to handle when recording is finished**
extension VideoRecorder: AVCaptureFileOutputRecordingDelegate {
    func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        if let error = error {
            print("[VideoRecorder] ERROR: \(error.localizedDescription)")
            return
        }

        print("[VideoRecorder] Video saved at: \(outputFileURL.absoluteString)")
        methodChannel?.invokeMethod("videoSaved", arguments: outputFileURL.absoluteString)
    }
}
