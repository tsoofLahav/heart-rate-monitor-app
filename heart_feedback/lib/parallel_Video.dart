import 'dart:io';
import 'dart:async';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:path_provider/path_provider.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:audioplayers/audioplayers.dart';
import 'package:vibration/vibration.dart'; // Needed for haptic feedback

class BiofeedbackScreen extends StatefulWidget {
  final String mode; // Mode selection flag

  BiofeedbackScreen({required this.mode});

  @override
  _BiofeedbackScreenState createState() => _BiofeedbackScreenState();
}

class _BiofeedbackScreenState extends State<BiofeedbackScreen> {
  CameraController? _cameraController;
  bool _isRecording = false;
  String? _videoPath;
  List<double> _timeIntervals = [];
  double _bpm = 0;
  bool _unstableReading = false;
  bool _newStart = false;
  final AudioPlayer _audioPlayer = AudioPlayer();

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  //////////////////////////////////////////////////////////////////////////////
  // CAMERA INITIALIZATION
  //////////////////////////////////////////////////////////////////////////////

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

  //////////////////////////////////////////////////////////////////////////////
  // START VIDEO RECORDING & PROCESSING
  //////////////////////////////////////////////////////////////////////////////

  Future<void> _startBiofeedback() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    _isRecording = true;
    _loopRecording();

    setState(() {});
  }

  //////////////////////////////////////////////////////////////////////////////
  // RECORDING VIDEO IN A LOOP & SENDING TO BACKEND
  //////////////////////////////////////////////////////////////////////////////

  Future<void> _loopRecording() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    _isRecording = true;
    
    // Turn ON flash only once at the start of recording session
    await _cameraController!.setFlashMode(FlashMode.torch);

    await _cameraController!.startVideoRecording();

    while (_isRecording) {
      await Future.delayed(Duration(seconds: 3));

      if (_isRecording) {
        try {
          final file = await _cameraController!.stopVideoRecording();
          final filePath = file.path;

          await _sendVideoToBackend(filePath);

          if (_isRecording) {
            await _cameraController!.startVideoRecording();
          }
        } catch (e) {
          print("Error stopping or starting video recording: $e");
        }
      }
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // SEND VIDEO TO BACKEND & RECEIVE DATA
  //////////////////////////////////////////////////////////////////////////////

  Future<void> _sendVideoToBackend(String filePath) async {
    var uri = Uri.parse("https://heart-rate-monitor-app.onrender.com/process_video");

    var request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('video', filePath));

    var startTime = DateTime.now(); // Start measuring time

    try {
      var response = await request.send();
      var endTime = DateTime.now(); // End measuring time
      print("Backend response time: ${endTime.difference(startTime).inMilliseconds} ms");

      if (response.statusCode == 200) {
        var jsonResponse = await response.stream.bytesToString();

        // Ensure response is not empty before parsing
        if (jsonResponse.isNotEmpty) {
          var data = json.decode(jsonResponse);

          // ✅ Check for server error first
          if (data.containsKey('server_error') && data['server_error'] == true) {
            print("Server error detected. Skipping processing.");
            return; // Stop execution
          }

          // ✅ Ensure required values exist before using them
          if (data.containsKey('heart_rate') && data['heart_rate'] != null) {
            _handleBackendResponse(data);
          } else {
            print("Error: 'heart_rate' is missing or null in response.");
          }
        } else {
          print("Error: Received empty response from backend.");
        }
      } else {
        print("Failed to send video, status code: ${response.statusCode}");
      }
    } catch (e) {
      print("Error sending video: $e");
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // HANDLE RESPONSE FROM BACKEND
  //////////////////////////////////////////////////////////////////////////////

  void _handleBackendResponse(Map<String, dynamic> data) {
    setState(() {
      _unstableReading = data['not_reading'];
      _bpm = data['heart_rate'];
      _timeIntervals = List<double>.from(data['intervals']);
      _newStart = data['startNew'];
    });

    if (_timeIntervals.isNotEmpty) {
      if (widget.mode == "audio") {
        _playSoundsWithIntervals();
      } else if (widget.mode == "haptic") {
        _triggerHapticFeedback();
      } else if (widget.mode == "visual") {
        _updateVisualFeedback();
      }
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // PLAY SOUND BASED ON INTERVAL TIMING
  //////////////////////////////////////////////////////////////////////////////

  void _playSoundsWithIntervals() async {
    if (_timeIntervals.isEmpty || _timeIntervals.length == 1) return;

    if (_newStart) {
      await _playSound();
      await Future.delayed(Duration(seconds: _timeIntervals[0].toInt()));
    }

    for (int i = _newStart ? 1 : 0; i < _timeIntervals.length - 1; i++) {
      await Future.delayed(Duration(seconds: _timeIntervals[i].toInt()));
      await _playSound();
    }
  }

  Future<void> _playSound() async {
    await _audioPlayer.play(AssetSource('assets/boom.wav'));
  }

  //////////////////////////////////////////////////////////////////////////////
  // HAPTIC FEEDBACK
  //////////////////////////////////////////////////////////////////////////////

  void _triggerHapticFeedback() {
    for (double interval in _timeIntervals) {
      Future.delayed(Duration(milliseconds: (interval * 1000).toInt()), () {
        Vibration.vibrate(duration: 100);
      });
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // VISUAL FEEDBACK
  //////////////////////////////////////////////////////////////////////////////

  void _updateVisualFeedback() {
    print("Visual feedback triggered!");
    // TODO: Implement visual cue logic here
  }

  //////////////////////////////////////////////////////////////////////////////
  // STOP VIDEO RECORDING
  //////////////////////////////////////////////////////////////////////////////

  Future<void> _stopBiofeedback() async {
    if (_isRecording) {
      _isRecording = false;

      try {
        await _cameraController!.stopVideoRecording();
      } catch (e) {
        print("Error stopping video recording: $e");
      }

      // Turn OFF flash only when stopping biofeedback
      await _cameraController!.setFlashMode(FlashMode.off);

      setState(() {});
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // CLEANUP RESOURCES
  //////////////////////////////////////////////////////////////////////////////

  @override
  void dispose() {
    _cameraController?.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  //////////////////////////////////////////////////////////////////////////////
  // UI BUILD FUNCTION
  //////////////////////////////////////////////////////////////////////////////

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black, // Black background
      appBar: AppBar(title: Text('Biofeedback Screen')),
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
          Text(
            _unstableReading ? "Unstable reading, place your finger" : "BPM: $_bpm",
            style: TextStyle(
                fontSize: 18,
                fontWeight: FontWeight.bold,
                color: _unstableReading ? Colors.red : Colors.white),
          ),
          SizedBox(height: 20),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              ElevatedButton(
                onPressed: _isRecording ? null : _startBiofeedback,
                child: Text('Play'),
              ),
              SizedBox(width: 20),
              ElevatedButton(
                onPressed: _isRecording ? _stopBiofeedback : null,
                child: Text('Stop'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
