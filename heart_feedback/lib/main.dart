import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:audioplayers/audioplayers.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'dart:convert';
import 'dart:async';
import 'dart:io';

List<CameraDescription> cameras = [];

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    cameras = await availableCameras();
  } on CameraException catch (e) {
    print('Error in fetching the cameras: $e');
  }
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: HeartRateMonitor(),
    );
  }
}

class HeartRateMonitor extends StatefulWidget {
  @override
  _HeartRateMonitorState createState() => _HeartRateMonitorState();
}

class _HeartRateMonitorState extends State<HeartRateMonitor> {
  CameraController? _controller;
  AudioPlayer _audioPlayer = AudioPlayer();
  double _heartRate = 0.0;
  bool _isRecording = false;
  Timer? _audioTimer;
  int _currentPeakIndex = 0;
  List<int> _peaks = [];
  List<DateTime> _allPeaksTimestamps = [];
  bool _isProcessing = false;
  bool _unstableReading = false;
  Timer? _bpmTimer;

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    if (cameras.isNotEmpty) {
      _controller = CameraController(cameras[0], ResolutionPreset.low, enableAudio: false);
      try {
        await _controller!.initialize();
        _controller!.setFlashMode(FlashMode.torch);
        setState(() {});
      } catch (e) {
        print('Error initializing camera: $e');
      }
    } else {
      print('No camera is available.');
    }
  }

  void _startContinuousRecording() async {
    if (_controller != null && _controller!.value.isInitialized) {
      setState(() {
        _isRecording = true;
        _unstableReading = false;
      });
      await _controller!.startVideoRecording(); // Start continuous recording
      _processContinuousFrames();  // Begin processing video chunks in the background
    }
  }

  void _stopRecording() {
    setState(() {
      _isRecording = false;
      _audioTimer?.cancel();
      _audioPlayer.stop();
    });
    _controller?.stopVideoRecording();  // Stop continuous recording
  }

  Future<void> _processContinuousFrames() async {
    final directory = await getApplicationDocumentsDirectory();
    final videoPath = '${directory.path}/heart_rate_video.mp4';

    while (_isRecording) {
      await Future.delayed(Duration(seconds: 1));  // Change to 1 second
      XFile videoFile = await _controller!.stopVideoRecording();  // Stop temporarily to split
      await _controller!.startVideoRecording();  // Restart recording

      final File newFile = await File(videoFile.path).copy(videoPath);
      if (await newFile.exists()) {
        _sendVideoToBackend(newFile);  // Send this chunk to backend
      }
    }
  }

  Future<void> _sendVideoToBackend(File videoFile) async {
    if (_isProcessing) return;  // Prevent multiple concurrent requests
    _isProcessing = true;

    try {
      var request = http.MultipartRequest('POST', Uri.parse('https://heart-rate-monitor-app.onrender.com/process_video'));
      request.files.add(await http.MultipartFile.fromPath('video', videoFile.path));


      var response = await request.send();
      var responseBody = await response.stream.bytesToString();

      if (response.statusCode == 200) {
        var result = jsonDecode(responseBody);
        setState(() {
          _peaks = List<int>.from(result['peaks']);  // Use the peaks sent by backend
          _heartRate = result['heart_rate'];
          _playAudioByPeaks();  // Play sounds for detected beats
        });
      } else {
        print('Error response from server: ${response.statusCode} ${response.reasonPhrase}');
        print('Response body: $responseBody');
      }
    } catch (e) {
      print('Exception caught: $e');
    } finally {
      _isProcessing = false;
    }
  }

  void _playAudioByPeaks() {
    if (_peaks.isNotEmpty) {
      _currentPeakIndex = 0;
      _audioTimer?.cancel();
      _playSound();
    }
  }

  Future<void> _playSound() async {
    if (_currentPeakIndex < _peaks.length) {
      await _audioPlayer.play(AssetSource('boom.mp3'));
      int interval = (_peaks[_currentPeakIndex] * 1000 ~/ 30);  // Assuming 30 FPS
      _currentPeakIndex++;
      _audioTimer = Timer(Duration(milliseconds: interval), _playSound);
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    _audioTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.red[100],
      appBar: AppBar(title: Text('Heart Rate Monitor')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (_controller != null && _controller!.value.isInitialized)
              Container(
                width: 200,
                height: 200,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.red, width: 4),
                ),
                child: ClipOval(child: CameraPreview(_controller!)),
              )
            else
              Center(child: Text('Initializing camera...')),
            SizedBox(height: 20),
            Text(
              'Heart Rate: ${_heartRate.toStringAsFixed(2)} BPM',
              style: TextStyle(fontSize: 24),
            ),
            if (_unstableReading)
              Text(
                'Don\'t move',
                style: TextStyle(fontSize: 24, color: Colors.red),
              ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _isRecording ? null : _startContinuousRecording,
              child: Text('Start', style: TextStyle(fontSize: 24)),
              style: ElevatedButton.styleFrom(
                padding: EdgeInsets.symmetric(horizontal: 40, vertical: 20),
                backgroundColor: Colors.green,
              ),
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: _isRecording ? _stopRecording : null,
              child: Text('Stop', style: TextStyle(fontSize: 24)),
              style: ElevatedButton.styleFrom(
                padding: EdgeInsets.symmetric(horizontal: 40, vertical: 20),
                backgroundColor: Colors.red,
              ),
            ),
          ],
        ),
      ),
    );
  }
}