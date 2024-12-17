import 'package:camera/camera.dart';

class CameraService {
  CameraController? _controller;

  Future<CameraController?> initializeCamera(List<CameraDescription> cameras) async {
    if (cameras.isNotEmpty) {
      _controller = CameraController(cameras[0], ResolutionPreset.low, enableAudio: false);
      await _controller!.initialize();
      await _controller!.setFlashMode(FlashMode.torch);
      return _controller;
    } else {
      print('No camera is available.');
      return null;
    }
  }

  CameraController? get controller => _controller;

  void dispose() {
    _controller?.dispose();
  }
}
