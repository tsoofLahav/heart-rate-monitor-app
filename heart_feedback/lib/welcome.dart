import 'package:flutter/material.dart';
import 'dart:async';
import 'selection_screen.dart';

class WelcomePage extends StatefulWidget {
  @override
  _WelcomePageState createState() => _WelcomePageState();
}

class _WelcomePageState extends State<WelcomePage> {
  @override
  void initState() {
    super.initState();
    // Navigate to selection page after 1 second
    Timer(Duration(seconds: 1), () {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (context) => SelectionScreen()), // Replace with actual selection page
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            AnimatedOpacity(
              opacity: 1.0,
              duration: Duration(milliseconds: 800),
              child: Text(
                "Welcome to Heart Monitor",
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Colors.white,
                  fontFamily: ".SF Pro Display", // San Francisco
                ),
              ),
            ),
            SizedBox(height: 20),
            Image.asset("assets/pulse.png", width: 100, height: 100),
          ],
        ),
      ),
    );
  }
}
