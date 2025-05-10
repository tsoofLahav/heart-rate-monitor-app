import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'selection_screen.dart';

class GuessingScreen extends StatefulWidget {
  final int sessionId; // Session ID needed for backend request

  GuessingScreen({required this.sessionId});

  @override
  _GuessingScreenState createState() => _GuessingScreenState();
}

class _GuessingScreenState extends State<GuessingScreen> {
  final TextEditingController _guessController = TextEditingController();

  Future<void> _submitGuess() async {
    if (_guessController.text.isEmpty) return;

    int guessedBpm = int.tryParse(_guessController.text) ?? 0; // Convert input to integer

    var url = Uri.parse("https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/data/end_session"); // Replace with your backend URL
    var response = await http.post(
      url,
      headers: {"Content-Type": "application/json"},
      body: json.encode({
        "session_id": widget.sessionId,
        "guessed_bpm": guessedBpm,
      }),
    );

    if (response.statusCode == 200) {
      // Navigate back to selection screen after submission
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => SelectionScreen()),
      );
    } else {
      print("Error sending guess: ${response.body}");
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text("Guess Your Heart Rate")),
      body: Center(
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: 30.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                "Insert Heart Rate Guess:",
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              SizedBox(height: 20),
              TextField(
                controller: _guessController,
                keyboardType: TextInputType.number, // Opens numeric keyboard
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 24, color: Colors.white),
                decoration: InputDecoration(
                  filled: true,
                  fillColor: Colors.grey[800],
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                  hintText: "Enter BPM",
                  hintStyle: TextStyle(color: Colors.white70),
                ),
              ),
              SizedBox(height: 30),
              ElevatedButton(
                onPressed: _submitGuess,
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blueAccent,
                  padding: EdgeInsets.symmetric(vertical: 15, horizontal: 50),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(10),
                  ),
                ),
                child: Text(
                  "Insert",
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
