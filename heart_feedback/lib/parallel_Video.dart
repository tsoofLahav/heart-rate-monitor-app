import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:video_player/video_player.dart';
import 'package:path_provider/path_provider.dart';

class ParallelVideoPage extends StatefulWidget {
  @override
  _ParallelVideoPageState createState() => _ParallelVideoPageState();
}

class _ParallelVideoPageState extends State<ParallelVideoPage> {
  CameraController? _cameraController;
  VideoPlayerController? _videoController;
  bool _isRecording = false;
  String? _videoPath;

  @override
  void initState() {
    super.initState();
    _initCamera();
    _initVideoPlayer();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final backCamera = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back);

    _cameraController = CameraController(
      backCamera,
      ResolutionPreset.medium,
      enableAudio: false,
    );
    await _cameraController!.initialize();
    setState(() {});
  }

  void _initVideoPlayer() {
    _videoController = VideoPlayerController.asset('assets/video.mp4')
      ..setLooping(true)
      ..initialize().then((_) {
        setState(() {});
      });
  }

  Future<void> _startParallelProcessing() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;
    
    final directory = await getApplicationDocumentsDirectory();
    _videoPath = '\${directory.path}/\${DateTime.now().millisecondsSinceEpoch}.mp4';
    await _cameraController!.startVideoRecording();
    _videoController?.play();
    setState(() {
      _isRecording = true;
    });
    
    _loopRecording();
  }

  Future<void> _loopRecording() async {
    while (_isRecording) {
      await Future.delayed(Duration(seconds: 3));
      if (_isRecording) {
        final file = await _cameraController!.stopVideoRecording();
        final fileSize = await File(file.path).length();
        final directory = await getApplicationDocumentsDirectory();
        _videoPath = '${directory.path}/${DateTime.now().millisecondsSinceEpoch}.mp4';
        print("Video saved at: $_videoPath , Size: $fileSize bytes");
        await _cameraController!.startVideoRecording();
      }
    }
  }

  Future<void> _stopParallelProcessing() async {
    if (_isRecording) {
      _isRecording = false;
      await _cameraController!.stopVideoRecording();
      _videoController?.pause();
      setState(() {});
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _videoController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Parallel Video Record & Play')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _cameraController != null && _cameraController!.value.isInitialized
              ? AspectRatio(
                  aspectRatio: _cameraController!.value.aspectRatio,
                  child: CameraPreview(_cameraController!),
                )
              : CircularProgressIndicator(),
          SizedBox(height: 20),
          _videoController != null && _videoController!.value.isInitialized
              ? AspectRatio(
                  aspectRatio: _videoController!.value.aspectRatio,
                  child: VideoPlayer(_videoController!),
                )
              : CircularProgressIndicator(),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton(
                onPressed: _isRecording ? null : _startParallelProcessing,
                child: Text('Start'),
              ),
              SizedBox(width: 20),
              ElevatedButton(
                onPressed: _isRecording ? _stopParallelProcessing : null,
                child: Text('Stop'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
