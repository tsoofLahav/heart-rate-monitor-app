import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:intl/intl.dart';

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
    final response = await http.get(Uri.parse(
        'https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/data/get_sessions'));

    if (response.statusCode == 200) {
      List fetchedSessions = json.decode(response.body);
      print("✅ Fetched sessions: $fetchedSessions");

      setState(() {
        sessions = fetchedSessions;
      });
    } else {
      print("❌ Failed to fetch sessions: ${response.statusCode}");
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
              "Guessed BPM: ${session['guessed_bpm'] ?? 'N/A'} | Real BPM: ${session['real_bpm'] != null ? session['real_bpm'].toInt() : 'N/A'}",
              style: TextStyle(color: Colors.grey),
            ),
            onTap: () {
              Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => SessionDetailsPage(
                    sessionId: session['session_id'],
                    guessedBpm: session['guessed_bpm'] ?? 0,
                    realBpm: session['real_bpm'] ?? 0,
                  ),
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
  final double guessedBpm;
  final double realBpm;

  SessionDetailsPage({
    required this.sessionId,
    required this.guessedBpm,
    required this.realBpm,
  });

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
    final response = await http.get(Uri.parse(
        'https://monitorflaskbackend-aaadajegfjd7b9hq.israelcentral-01.azurewebsites.net/data/get_session_details?session_id=${widget.sessionId}'));

    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);
      print("✅ Fetched session details: $data");

      if (data.isNotEmpty) {
        double firstTimestamp = parseCustomTimestamp(data.first['timestamp'])
            .millisecondsSinceEpoch
            .toDouble();

        setState(() {
          bpmData = data
              .map<FlSpot>((e) => FlSpot(
                    parseTimestamp(e['timestamp'], firstTimestamp),
                    e['bpm'].toDouble(),
                  ))
              .toList();

          hrvData = data
              .map<FlSpot>((e) => FlSpot(
                    parseTimestamp(e['timestamp'], firstTimestamp),
                    e['hrv'].toDouble(),
                  ))
              .toList();
        });
      } else {
        print("⚠️ No session details found.");
      }
    } else {
      print("❌ Failed to fetch session details: ${response.statusCode}");
    }
  }

  /// Fix for timestamp parsing (handles non-ISO format)
  DateTime parseCustomTimestamp(String timestamp) {
    return DateFormat("EEE, dd MMM yyyy HH:mm:ss 'GMT'").parseUtc(timestamp);
  }

  /// Normalizes timestamps so the graph starts at zero
  double parseTimestamp(String timestamp, double firstTimestamp) {
    DateTime dateTime = parseCustomTimestamp(timestamp);
    return (dateTime.millisecondsSinceEpoch - firstTimestamp) / 1000;
  }

  Widget buildGraph(List<FlSpot> data, String title, Color color) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.all(16.0),
          child: Text(
            title,
            style: TextStyle(color: Colors.white, fontSize: 18),
          ),
        ),
        SizedBox(
          height: 250,
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Container(
              width: data.length * 30.0, // Ensures graph spreads across width
              height: 250,
              child: LineChart(
                LineChartData(
                  backgroundColor: Colors.black,
                  titlesData: FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 40,
                        interval: (data.isNotEmpty) ? (data.map((e) => e.y).reduce((a, b) => a > b ? a : b) / 4) : 10,
                        getTitlesWidget: (value, meta) {
                          return Text(value.toStringAsFixed(1), style: TextStyle(color: Colors.white, fontSize: 12));
                        },
                      ),
                    ),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        interval: (data.isNotEmpty) ? (data.last.x / 4) : 10,
                        getTitlesWidget: (value, meta) {
                          return Text("${value.toInt()}s", style: TextStyle(color: Colors.white, fontSize: 12));
                        },
                      ),
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  gridData: FlGridData(show: true),
                  lineBarsData: [
                    LineChartBarData(
                      spots: data,
                      color: color,
                      isCurved: true,
                      dotData: FlDotData(show: false),
                      barWidth: 3,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
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
          buildGraph(bpmData, 'BPM Over Time', Colors.blue),
          buildGraph(hrvData, 'HRV Over Time', Colors.red),
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              "Guessed BPM: ${widget.guessedBpm.toInt()} | Real BPM: ${widget.realBpm.toInt()}",
              style: TextStyle(color: Colors.white, fontSize: 18),
            ),
          ),
        ],
      ),
    );
  }
}
