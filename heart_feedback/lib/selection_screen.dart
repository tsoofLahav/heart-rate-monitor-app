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
          SizedBox(height: 40), // More spacing at the top
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Text(
              "Choose Feedback Method",
              style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          SizedBox(height: 50), // More spacing before buttons
          _buildButton(context, "Visual", "visual"),
          SizedBox(height: 20), // Increased spacing between buttons
          _buildButton(context, "Haptic", "haptic"),
          SizedBox(height: 20),
          _buildButton(context, "Audio", "audio"),
          Spacer(),
          Padding(
            padding: const EdgeInsets.only(bottom: 30.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildIconButton(context, 'assets/history_icon.png', 40, () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => SessionListPage()),
                  );
                }),
                _buildIconButton(context, 'assets/profile_icon.png', 40, () {
                  Navigator.pushNamed(context, '/profile');
                }),
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
    return SizedBox(
      width: MediaQuery.of(context).size.width * 0.7, // Buttons spread more across the screen
      height: 60, // Larger button height
      child: ElevatedButton(
        style: ElevatedButton.styleFrom(
          backgroundColor: buttonColor,
          foregroundColor: Colors.black, // Button text color
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        ),
        onPressed: () {
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => BiofeedbackScreen(mode: mode),
            ),
          );
        },
        child: Text(label, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
      ),
    );
  }

  Widget _buildIconButton(BuildContext context, String assetPath, double size, VoidCallback onTap) {
    return IconButton(
      icon: Image.asset(assetPath),
      iconSize: size, // Smaller icons
      onPressed: onTap,
    );
  }
}
