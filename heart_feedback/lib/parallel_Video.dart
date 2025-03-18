import 'dart:async';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:audioplayers/audioplayers.dart';
import 'package:vibration/vibration.dart'; // Needed for haptic feedback
import 'dart:math';
import 'guessing_screen.dart';

class BiofeedbackScreen extends StatefulWidget {
  final String mode; // Mode selection flag

  BiofeedbackScreen({required this.mode});

  @override
  _BiofeedbackScreenState createState() => _BiofeedbackScreenState();
}

class _BiofeedbackScreenState extends State<BiofeedbackScreen> with SingleTickerProviderStateMixin{
  CameraController? _cameraController;
  bool _isRecording = false;
  List<double> _timeIntervals = [];
  int _bpm = 0;
  bool _unstableReading = false;
  bool _isPlaying = false;
  bool _loading = false;
  bool _serverError = false;
  final AudioPlayer _audioPlayer = AudioPlayer();
  late AnimationController _animationController;
  Future<Map<String, dynamic>>? _previousResponse; // Stores the last response
  Color _circleColor = Colors.blue; // Default color
  int _sessionId = 0; // Store session ID


  @override
  void initState() {
    super.initState();
    _initCamera();
    _animationController = AnimationController(
      vsync: this,
      duration: Duration(milliseconds: 100),
      lowerBound: 0.8,
      upperBound: 1.2,
    );
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
      imageFormatGroup: ImageFormatGroup.yuv420,
    );

    await _cameraController!.initialize();
    await _cameraController!.setExposureMode(ExposureMode.auto);
    await _cameraController!.setFocusMode(FocusMode.auto);
    await _cameraController!.lockCaptureOrientation();

    setState(() {});
  }

  //////////////////////////////////////////////////////////////////////////////
  // START VIDEO RECORDING & PROCESSING
  //////////////////////////////////////////////////////////////////////////////
  Future<void> _startBiofeedback() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    // Request new session ID from backend
    await _createNewSession();

    if (_sessionId == 0) {
      print("Failed to start session, sessionId is null.");
      return;
    }

    _isRecording = true;
    _loopRecording();
    setState(() {});
  }


  Future<void> _createNewSession() async {
    var url = Uri.parse("https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/data/start_session"); // Replace with actual backend URL
    var response = await http.post(url, headers: {"Content-Type": "application/json"});

    if (response.statusCode == 200) {
      var jsonResponse = json.decode(response.body);
      setState(() {
        _sessionId = jsonResponse["session_id"]; // Store session ID
      });
      print("New session started with ID: $_sessionId");
    } else {
      print("Failed to start session: ${response.body}");
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // RECORDING VIDEO IN A LOOP & SENDING TO BACKEND
  //////////////////////////////////////////////////////////////////////////////

  Future<void> _loopRecording() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) return;

    _isRecording = true;
    await _cameraController!.setFlashMode(FlashMode.torch);
    await _cameraController!.startVideoRecording();

    while (_isRecording) {
      await Future.delayed(Duration(seconds: 5));

      if (_isRecording) {
        try {
          final file = await _cameraController!.stopVideoRecording();
          final filePath = file.path;

          // ✅ 1. Process previous response first (WAIT before restarting)
          await _receiveResponse();

          // ✅ 2. Send the new video to the backend
          _sendVideoToBackend(filePath);

          // ✅ 3. Restart recording AFTER response is processed
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
  
  // ✅ HANDLE RECEIVING RESPONSE
  Future<void> _receiveResponse() async {
    if (_previousResponse != null) {
      try {

        final data = await _previousResponse!;
        if (mounted) {
          if (data.isNotEmpty) {
            _handleBackendResponse(data);
          } else {
          }
        }

      } catch (e) {
        print("Error receiving backend response: $e");
      } finally {
        _previousResponse = null;  // Clear response after processing
      }
    }
  }

  void _sendVideoToBackend(String filePath) {
    var uri = Uri.parse("https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/process_video");

    var request = http.MultipartRequest('POST', uri);

    http.MultipartFile.fromPath('video', filePath).then((file) {
      request.files.add(file);

      _previousResponse = request.send().then<Map<String, dynamic>>((response) async {

        if (response.statusCode == 200) {
          var jsonResponse = await response.stream.bytesToString();
          return jsonResponse.isNotEmpty ? json.decode(jsonResponse) as Map<String, dynamic> : {};
        }
        return {};
      }).catchError((e) {
        print("Error sending video: $e");
        return <String, dynamic>{};
      });
    });
  }

  //////////////////////////////////////////////////////////////////////////////
  // HANDLE RESPONSE FROM BACKEND
  //////////////////////////////////////////////////////////////////////////////

  void _handleBackendResponse(Map<String, dynamic> data) {
    setState(() {
      _loading = false;
      _serverError = false;
      _unstableReading = false;
    });

    if (data.containsKey("server_error")) {
      setState(() => _serverError = true);
      return;
    }

    if (data.containsKey("loading")) {
      setState(() => _loading = true);
      return;
    }

    if (data.containsKey("not_reading")) {
      setState(() => _unstableReading = data["not_reading"]);
      return;
    }

    if (data.containsKey("bpm") && data.containsKey("intervals")) {
      setState(() {
        _bpm = data["bpm"].toInt(); // Convert to int
        _timeIntervals = List<double>.from(data["intervals"]);
      });

      if (_timeIntervals.isNotEmpty) {
        switch (widget.mode) {
          case "audio":
            _playSoundsWithIntervals(); // Run in parallel
            break;
          case "haptic":
            _triggerHapticFeedback();
            break;
          case "visual":
            _playVisualFeedback();
            break;
        }
      }
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // PLAY SOUND BASED ON INTERVAL TIMING
  //////////////////////////////////////////////////////////////////////////////


  Future<void> _playSoundsWithIntervals() async {
    if (_isPlaying || _timeIntervals.length < 2) return; // Prevent overlap
    _isPlaying = true;

    await Future.delayed(Duration(milliseconds: (_timeIntervals[0] * 1000).toInt())); // Wait first interval

    for (int i = 1; i < _timeIntervals.length - 1; i++) {
      await _playSound();
      await Future.delayed(Duration(milliseconds: (_timeIntervals[i] * 1000).toInt()));
    }

    // ✅ Trigger before the last interval but don't count its time
    await _playSound();

    _isPlaying = false; // Reset flag after completion
  }

  Future<void> _playSound() async {
    await _audioPlayer.play(AssetSource('boom.wav'));
  }

  //////////////////////////////////////////////////////////////////////////////
  // HAPTIC FEEDBACK
  //////////////////////////////////////////////////////////////////////////////

  Future<void> _triggerHapticFeedback() async {
    if (_timeIntervals.length < 2) return; // Need at least 2 intervals

    await Future.delayed(Duration(milliseconds: (_timeIntervals[0] * 1000).toInt())); // Wait first interval

    for (int i = 1; i < _timeIntervals.length - 1; i++) {
      Vibration.vibrate(duration: 50);
      await Future.delayed(Duration(milliseconds: (_timeIntervals[i] * 1000).toInt()));
    }

    // ✅ Trigger before the last interval but don't count its time
    Vibration.vibrate(duration: 50);
  }

  //////////////////////////////////////////////////////////////////////////////
  // VISUAL FEEDBACK
  //////////////////////////////////////////////////////////////////////////////

  Future<void> _playVisualFeedback() async {
    if (_timeIntervals.length < 2) return; // Need at least 2 intervals

    await Future.delayed(Duration(milliseconds: (_timeIntervals[0] * 1000).toInt())); // Wait first interval

    for (int i = 1; i < _timeIntervals.length - 1; i++) {
      setState(() {
        _circleColor = Colors.primaries[Random().nextInt(Colors.primaries.length)]; // Random color change
      });
      await Future.delayed(Duration(milliseconds: (_timeIntervals[i] * 1000).toInt()));
    }

    // ✅ Final color update before last interval
    setState(() {
      _circleColor = Colors.primaries[Random().nextInt(Colors.primaries.length)];
    });
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
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => GuessingScreen(sessionId: _sessionId)), // Replace with actual screen
      );
    }
  }

  //////////////////////////////////////////////////////////////////////////////
  // CLEANUP RESOURCES
  //////////////////////////////////////////////////////////////////////////////
    @override
  void dispose() {
    _animationController.dispose();
    _cameraController?.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }
  //////////////////////////////////////////////////////////////////////////////
  // UI
  //////////////////////////////////////////////////////////////////////////////

  @override
  Widget build(BuildContext context) {
    // Determine the message to display
    String message = "Place finger on camera"; // Default message

    if (_loading) {
      message = "Loading...";
    } else if (_serverError) {
      message = "Error, please restart the app or ask for support";
    } else if (_unstableReading) {
      message = "Please don't move/ place your finger";
    } else if (_bpm > 0) { // Display BPM only if valid
      message = "BPM: $_bpm";
    }

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
            AnimatedBuilder(
              animation: _animationController,
              builder: (context, child) {
                return Transform.scale(
                  scale: _animationController.value,
                  child: Container(
                    width: 100,
                    height: 100,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: const Color.fromARGB(255, 183, 183, 183), // Customize color if needed
                    ),
                  ),
                );
              },
            ),
          SizedBox(height: 20),
          Text(
            message, // Dynamically updated message
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: _serverError ? Colors.red : Colors.white, // Red for errors
            ),
            textAlign: TextAlign.center,
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
