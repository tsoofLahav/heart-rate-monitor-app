import 'package:camera/camera.dart';

class CameraService {
  CameraController? _controller;

  Future<CameraController?> initializeCamera(List<CameraDescription> cameras) async {
    if (cameras.isNotEmpty) {
      _controller = CameraController(
        cameras[0], 
        ResolutionPreset.low, 
        enableAudio: false,
      );

      try {
        await _controller!.initialize();
        print("Camera initialized with resolution: ${_controller!.value.previewSize}");
        await _controller!.setFlashMode(FlashMode.torch);
        print("Flashlight enabled in torch mode");
      } catch (e) {
        print("Error initializing camera: $e");
      }

      return _controller;
    } else {
      print('No camera is available.');
      return null;
    }
  }

  CameraController? get controller => _controller;

  // Dispose method to clean up resources
  void dispose() {
    _controller?.dispose();
    print("CameraController disposed.");
  }
}
