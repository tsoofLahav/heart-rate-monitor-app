import 'package:flutter/material.dart';
import 'parallel_Video.dart';
import 'history.dart';
import 'pilote_data.dart';

class SelectionScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(title: Text('Personal Heart Monitor')),
      body: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          SizedBox(height: 40),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: Text(
              "Choose Feedback Method",
              style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
              textAlign: TextAlign.center,
            ),
          ),
          SizedBox(height: 80),
          _buildButton(context, "Visual", "visual"),
          SizedBox(height: 50),
          _buildButton(context, "Haptic", "haptic"),
          SizedBox(height: 50),
          _buildButton(context, "Audio", "audio"),
          Spacer(),
          Padding(
            padding: const EdgeInsets.only(bottom: 30.0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildIconButton(context, 'assets/history_icon.png', () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => SessionListPage()),
                  );
                }),
                _buildIconButton(context, 'assets/profile_icon.png', () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => const SessionDataPage()),
                  );
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
    bool isDisabled = (mode != 'audio');

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

    Widget button = Opacity(
      opacity: isDisabled ? 0.4 : 1.0,
      child: SizedBox(
        width: MediaQuery.of(context).size.width * 0.5,
        height: 50,
        child: ElevatedButton(
          style: ElevatedButton.styleFrom(
            backgroundColor: buttonColor,
            foregroundColor: Colors.black,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          ),
          onPressed: isDisabled
              ? () {} // Disabled buttons are visible but inactive
              : () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(builder: (context) => BiofeedbackScreen(mode: mode)),
                  );
                },
          child: Text(label, style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
        ),
      ),
    );

    if (!isDisabled) return button;

    return Stack(
      alignment: Alignment.center,
      children: [
        button,
        Positioned.fill(
          child: CustomPaint(
            painter: _DiagonalLinePainter(),
          ),
        ),
      ],
    );
  }

  Widget _buildIconButton(BuildContext context, String assetPath, VoidCallback onTap) {
    return IconButton(
      icon: Image.asset(
        assetPath,
        width: MediaQuery.of(context).size.width * 0.1,
        height: MediaQuery.of(context).size.width * 0.1,
      ),
      onPressed: onTap,
    );
  }
}

class _DiagonalLinePainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white
      ..strokeWidth = 3;
    canvas.drawLine(Offset(0, 0), Offset(size.width, size.height), paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
