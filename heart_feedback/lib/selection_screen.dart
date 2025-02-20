import 'package:flutter/material.dart';
import 'parallel_Video.dart';

class SelectionScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black, // Black background
      appBar: AppBar(title: Text('Choose Biofeedback Mode')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            _buildButton(context, "Visual", "visual"),
            _buildButton(context, "Haptic", "haptic"),
            _buildButton(context, "Audio", "audio"),
          ],
        ),
      ),
    );
  }

  Widget _buildButton(BuildContext context, String label, String mode) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10.0),
      child: ElevatedButton(
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => BiofeedbackScreen(mode: mode),
            ),
          );
        },
        child: Text(label),
      ),
    );
  }
}
