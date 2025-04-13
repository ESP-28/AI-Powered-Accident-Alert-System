import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, Vibration } from 'react-native';
import { Accelerometer, Gyroscope } from 'expo-sensors';
import * as Location from 'expo-location';
import { Audio } from 'expo-av';
import { useKeepAwake } from 'expo-keep-awake';

export default function HomeScreen() {
  useKeepAwake();

  const [accel, setAccel] = useState({});
  const [gyro, setGyro] = useState({});
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [accidentDetected, setAccidentDetected] = useState(false);
  const [sound, setSound] = useState<Audio.Sound | null>(null);

  // 🔔 Siren sound
  const playSiren = async () => {
    const { sound } = await Audio.Sound.createAsync(
      require('../../assets/siren.mp3')
    );
    setSound(sound);
    await sound.playAsync();
  };

  // ☁️ Send data to Flask backend
  const sendAlertToCloud = async () => {
    try {
      // ✅ Always get latest location here
      let loc = await Location.getCurrentPositionAsync({});
      const latestLocation = loc.coords;
      console.log("📍 Sending location to server:", latestLocation);

      if (!latestLocation || !latestLocation.latitude || !latestLocation.longitude) {
        console.log("❌ Location unavailable. Aborting alert.");
        return;
      }

      const response = await fetch('http://192.168.1.16:5000/report-accident', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: latestLocation.latitude,
          longitude: latestLocation.longitude,
        }),
      });

      const result = await response.json();
      console.log("✅ Alert sent to backend:", result);
    } catch (error) {
      console.error("❌ Error sending alert:", error);
    }
  };

  useEffect(() => {
    Accelerometer.setUpdateInterval(500);
    Gyroscope.setUpdateInterval(500);

    const accelSub = Accelerometer.addListener(data => {
      setAccel(data);

      const threshold = 2.0;
      const isSpike =
        Math.abs(data.x) > threshold ||
        Math.abs(data.y) > threshold ||
        Math.abs(data.z) > threshold;

      if (isSpike && !accidentDetected) {
        setAccidentDetected(true);
        Vibration.vibrate(1000);
        playSiren();
        sendAlertToCloud();
      }
    });

    const gyroSub = Gyroscope.addListener(setGyro);

    // ✅ Get location on app load (optional for UI only)
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        console.log("❌ Location permission denied.");
        return;
      }

      let loc = await Location.getCurrentPositionAsync({});
      console.log("📍 Got current location (initial):", loc.coords);
      setLocation(loc.coords);
    })();

    return () => {
      accelSub.remove();
      gyroSub.remove();
      sound?.unloadAsync();
    };
  }, []);

  return (
    <View style={styles.container}>
      <Text style={styles.title}>🚗 Accident Detection</Text>

      {accidentDetected && (
        <Text style={styles.alert}>🚨 Accident Detected!</Text>
      )}

      <Text style={styles.label}>📦 Accelerometer:</Text>
      <Text style={styles.text}>
        X: {accel.x?.toFixed(2)} Y: {accel.y?.toFixed(2)} Z: {accel.z?.toFixed(2)}
      </Text>

      <Text style={styles.label}>🔁 Gyroscope:</Text>
      <Text style={styles.text}>
        X: {gyro.x?.toFixed(2)} Y: {gyro.y?.toFixed(2)} Z: {gyro.z?.toFixed(2)}
      </Text>

      <Text style={styles.label}>📍 Location:</Text>
      <Text style={styles.text}>Latitude: {location?.latitude}</Text>
      <Text style={styles.text}>Longitude: {location?.longitude}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
    backgroundColor: '#000',
  },
  title: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 20,
  },
  label: {
    fontSize: 16,
    color: '#f2f2f2',
    marginTop: 10,
  },
  text: {
    color: '#fff',
    fontSize: 15,
    marginBottom: 5,
  },
  alert: {
    color: '#ff3b3b',
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
  },
});
