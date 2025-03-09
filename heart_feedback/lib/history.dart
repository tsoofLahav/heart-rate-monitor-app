import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

class SessionListPage extends StatefulWidget {
  @override
  _SessionListPageState createState() => _SessionListPageState();
}

class _SessionListPageState extends State<SessionListPage> {
  List sessions = [];

  @override
  void initState() {
    super.initState();
    fetchSessions();
  }

  Future<void> fetchSessions() async {
    final response = await http.get(Uri.parse('https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/get_sessions'));
    if (response.statusCode == 200) {
      setState(() {
        sessions = json.decode(response.body);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text('Sessions', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.black,
      ),
      body: ListView.builder(
        itemCount: sessions.length,
        itemBuilder: (context, index) {
          var session = sessions[index];
          return ListTile(
            title: Text(
              "${session['start_time']}",
              style: TextStyle(color: Colors.white),
            ),
            subtitle: Text(
              "Guessed BPM: ${session['guessed_bpm']} | Real BPM: ${session['real_bpm']}",
              style: TextStyle(color: Colors.grey),
            ),
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => SessionDetailsPage(sessionId: session['session_id']),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

class SessionDetailsPage extends StatefulWidget {
  final int sessionId;
  
  SessionDetailsPage({required this.sessionId});
  
  @override
  _SessionDetailsPageState createState() => _SessionDetailsPageState();
}

class _SessionDetailsPageState extends State<SessionDetailsPage> {
  List<FlSpot> bpmData = [];
  List<FlSpot> hrvData = [];

  @override
  void initState() {
    super.initState();
    fetchSessionDetails();
  }

  Future<void> fetchSessionDetails() async {
    final response = await http.get(Uri.parse('https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/get_session_details?session_id=${widget.sessionId}'));
    
    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);

      setState(() {
        bpmData = data.map<FlSpot>((e) => FlSpot(
          e['timestamp'].toDouble(),  // Ensure timestamp is a double
          e['bpm'].toDouble(),
        )).toList();

        hrvData = data.map<FlSpot>((e) => FlSpot(
          e['timestamp'].toDouble(),
          e['hrv'].toDouble(),
        )).toList();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text('Session Details', style: TextStyle(color: Colors.white)),
        backgroundColor: Colors.black,
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text('BPM & HRV Over Time', style: TextStyle(color: Colors.white, fontSize: 18)),
          ),
          Expanded(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Container(
                width: bpmData.length * 10.0,
                height: 300,
                child: LineChart(
                  LineChartData(
                    backgroundColor: Colors.black,
                    titlesData: FlTitlesData(show: false),
                    borderData: FlBorderData(show: false),
                    gridData: FlGridData(show: false),
                    lineBarsData: [
                      LineChartBarData(spots: bpmData, color: Colors.blue, isCurved: true, dotData: FlDotData(show: false)),
                      LineChartBarData(spots: hrvData, color: Colors.red, isCurved: true, dotData: FlDotData(show: false)),
                    ],
                  ),
                ),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              "Guessed BPM: ${widget.sessionId} | Real BPM: ${widget.sessionId}",
              style: TextStyle(color: Colors.white, fontSize: 18),
            ),
          ),
        ],
      ),
    );
  }
}
