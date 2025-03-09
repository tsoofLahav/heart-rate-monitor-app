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
