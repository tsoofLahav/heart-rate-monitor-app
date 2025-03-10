import 'package:flutter/material.dart';
import 'parallel_Video.dart';
import 'history.dart';

class SelectionScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black, // Black background
      appBar: AppBar(title: Text('Personal Heart Monitor')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              "Choose Feedback Method",
              style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          _buildButton(context, "Visual", "visual"),
          _buildButton(context, "Haptic", "haptic"),
          _buildButton(context, "Audio", "audio"),
          Spacer(),
          Padding(
            padding: const EdgeInsets.only(bottom: 20.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                IconButton(
                  icon: Image.asset('assets/history_icon.png'),
                  iconSize: 50,
                  onPressed: () {
                    Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (context) => SessionListPage(),
                    ),
                  );
                  },
                ),
                IconButton(
                  icon: Image.asset('assets/profile_icon.png'),
                  iconSize: 50,
                  onPressed: () {
                    Navigator.pushNamed(context, '/profile');
                  },
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildButton(BuildContext context, String label, String mode) {
    Color buttonColor;
    switch (mode) {
      case 'visual':
        buttonColor = const Color.fromARGB(255, 139, 228, 218);
        break;
      case 'haptic':
        buttonColor = const Color.fromARGB(255, 195, 127, 121);
        break;
      case 'audio':
        buttonColor = const Color.fromARGB(255, 137, 210, 151);
        break;
      default:
        buttonColor = Colors.grey;
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10.0),
      child: ElevatedButton(
        style: ElevatedButton.styleFrom(
          backgroundColor: buttonColor,
          foregroundColor: Colors.black, // Button text color
        ),
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
