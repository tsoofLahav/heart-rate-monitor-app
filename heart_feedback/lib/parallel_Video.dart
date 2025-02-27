import 'dart:async';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:audioplayers/audioplayers.dart';
import 'package:vibration/vibration.dart'; // Needed for haptic feedback
import 'package:video_player/video_player.dart';

class BiofeedbackScreen extends StatefulWidget {
  final String mode; // Mode selection flag

  BiofeedbackScreen({required this.mode});

  @override
  _BiofeedbackScreenState createState() => _BiofeedbackScreenState();
}

class _BiofeedbackScreenState extends State<BiofeedbackScreen> {
  CameraController? _cameraController;
  bool _isRecording = false;
  List<double> _timeIntervals = [];
  double _bpm = 0;
  bool _unstableReading = false;
  bool _newStart = false;
  final AudioPlayer _audioPlayer = AudioPlayer();
  VideoPlayerController _videoController = VideoPlayerController.asset("assets/video.mp4");
  Future<Map<String, dynamic>>? _previousResponse; // Stores the last response

  @override
  void initState() {
    super.initState();
    _initCamera();
    _videoController = VideoPlayerController.asset("assets/video.mp4")..initialize();
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
    var uri = Uri.parse("https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/process_video");

    var request = http.MultipartRequest('POST', uri)
      ..files.add(await http.MultipartFile.fromPath('video', filePath));

    // ✅ Handle previous response before sending the next video
    if (_previousResponse != null) {
      _previousResponse!.then((data) {
        if (mounted && data.isNotEmpty) {
          _handleBackendResponse(data); // Process the previous response
        }
      });
    }

    // ✅ Send the video asynchronously without waiting
    _previousResponse = request.send().then<Map<String, dynamic>>((response) async {
      if (response.statusCode == 200) {
        var jsonResponse = await response.stream.bytesToString();
        return jsonResponse.isNotEmpty ? json.decode(jsonResponse) as Map<String, dynamic> : {};
      }
      return {};
    }).catchError((e) {
      print("Error sending video: $e");
      return Future.value(<String, dynamic>{});
    });
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
        _playVisualFeedback();
      }
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // PLAY SOUND BASED ON INTERVAL TIMING
  //////////////////////////////////////////////////////////////////////////////

  void _playSoundsWithIntervals() async {
    if (_timeIntervals.isEmpty) return;

    if (_newStart) {
      await _playSound();
    }

    for (double interval in _timeIntervals) {
      await Future.delayed(Duration(milliseconds: (interval * 1000).toInt()));
      await _playSound();
    }
  }

  Future<void> _playSound() async {
    await _audioPlayer.play(AssetSource('boom.wav'));
  }

  //////////////////////////////////////////////////////////////////////////////
  // HAPTIC FEEDBACK
  //////////////////////////////////////////////////////////////////////////////

  void _triggerHapticFeedback() async {
    if (_timeIntervals.isEmpty) return;

    if (_newStart) {
      Vibration.vibrate(duration: 50);
    }

    for (double interval in _timeIntervals) {
      await Future.delayed(Duration(milliseconds: (interval * 1000).toInt()));
      Vibration.vibrate(duration: 50);
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // VISUAL FEEDBACK
  //////////////////////////////////////////////////////////////////////////////

  void _playVisualFeedback() async {
    if (_timeIntervals.isEmpty) return;

    await _videoController.initialize();
    _videoController.setLooping(false);

    double originalDuration = _videoController.value.duration.inMilliseconds / 1000.0;

    if (_newStart) {
      double speed = originalDuration / _timeIntervals[0];
      _videoController.setPlaybackSpeed(speed);
      _videoController.play();
    }

    for (double interval in _timeIntervals) {
      double speed = originalDuration / interval;
      _videoController.setPlaybackSpeed(speed);
      _videoController.seekTo(Duration.zero);
      setState(() {
        _videoController.play();
      });
      await Future.delayed(Duration(milliseconds: (interval * 1000).toInt()));
    }

    // Play one more time with the last duration
    if (_timeIntervals.isEmpty) {
      double speed = originalDuration / _timeIntervals.last;
      _videoController.setPlaybackSpeed(speed);
      _videoController.seekTo(Duration.zero);
      setState(() {
        _videoController.play();
      });
    }
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
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black, // Black background
      appBar: AppBar(title: Text('Biofeedback Screen')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          ClipOval(
            child: SizedBox(
              width: 150, // Adjust size for small round preview
              height: 150,
              child: _cameraController != null && _cameraController!.value.isInitialized
                  ? CameraPreview(_cameraController!)
                  : CircularProgressIndicator(),
            ),
          ),
          SizedBox(height: 20),
          if (widget.mode == "visual")
            SizedBox(
              width: 300,
              height: 200,
              child: _videoController.value.isInitialized
                  ? AspectRatio(
                      aspectRatio: _videoController.value.aspectRatio,
                      child: VideoPlayer(_videoController),
                    )
                  : Container(),
            ),
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
