import 'package:flutter/material.dart';
import 'parallel_Video.dart'; // Import CameraPage

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      home: ParallelVideoPage(), // Redirect directly to CameraPage
    );
  }
}
