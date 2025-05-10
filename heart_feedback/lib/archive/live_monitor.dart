import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:torch_light/torch_light.dart';
import 'dart:math';

class CameraPage extends StatefulWidget {
  @override
  _CameraPageState createState() => _CameraPageState();
}

class _CameraPageState extends State<CameraPage> {
  CameraController? _controller;
  bool _isStreaming = false;
  double brightnessThreshold = 10.0; // Initial low value for first session
  final AudioPlayer _audioPlayer = AudioPlayer();
  List<double> brightnessValues = [];
  
  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    final backCamera = cameras.firstWhere(
        (camera) => camera.lensDirection == CameraLensDirection.back);

    _controller = CameraController(
      backCamera,
      ResolutionPreset.medium,
      enableAudio: false,
    );
    await _controller!.initialize();
    setState(() {});
  }

  Future<void> _startProcessing() async {
    if (_controller == null || !_controller!.value.isInitialized) return;

    await TorchLight.enableTorch(); // Turn on flashlight

    if (!_isStreaming) {
      _controller!.startImageStream((CameraImage image) {
        Future.microtask(() => _processFrame(image));
        _processFrame(image);
      });
      setState(() {
        _isStreaming = true;
      });
    }
  }

  Future<void> _stopProcessing() async {
    if (_controller == null) return;

    if (_isStreaming) {
      try {
        await Future.delayed(Duration(milliseconds: 50));
        await _controller!.stopImageStream();
      } catch (e) {
        print("Error stopping image stream: $e");
      }
      setState(() {
        _isStreaming = false;
      });
    }

    await TorchLight.disableTorch(); // Turn off flashlight
    _processBrightnessData();
  }

  void _processFrame(CameraImage image) async {
    double brightness = _calculateBrightness(image);
    if (brightnessValues.length > 1000) brightnessValues.removeAt(0);
    brightnessValues.add(brightness);
    if (brightness < brightnessThreshold) {
      _playSound();
    }
  }

  double _calculateBrightness(CameraImage image) {
    int sum = 0;
    int pixelCount = image.planes[0].bytes.length;

    for (int i = 0; i < pixelCount; i += 10) { // Sample pixels for efficiency
      sum += image.planes[0].bytes[i];
    }
    return sum / (pixelCount / 10);
  }

  Future<void> _playSound() async {
    await _audioPlayer.play(AssetSource('boom.wav'));
  }

  void _processBrightnessData() {
    if (brightnessValues.isEmpty) return;

    print("Processing");

    double avgBrightness = brightnessValues.reduce((a, b) => a + b) / brightnessValues.length;
    double stdDev = sqrt(brightnessValues.map((b) => pow(b - avgBrightness, 2)).reduce((a, b) => a + b) / brightnessValues.length);

    brightnessThreshold = avgBrightness - 0.5 * stdDev;
    print("Finish Processing. New brightnessThreshold: $brightnessThreshold");

    brightnessValues.clear(); // Reset for the next session
  }

  @override
  void dispose() {
    _controller?.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Camera Brightness Detector')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _controller != null && _controller!.value.isInitialized
              ? AspectRatio(
                  aspectRatio: _controller!.value.aspectRatio,
                  child: CameraPreview(_controller!),
                )
              : CircularProgressIndicator(),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton(
                onPressed: _isStreaming ? null : _startProcessing,
                child: Text('Start'),
              ),
              SizedBox(width: 20),
              ElevatedButton(
                onPressed: _isStreaming ? _stopProcessing : null,
                child: Text('Stop'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
