function updateTelemetry() {
    fetch('/get_orientation')
        .then(response => {
            if (!response.ok) throw new Error('Sunucu yanıt vermedi');
            return response.json();
        })
        .then(data => {
            document.getElementById('pitch').textContent = data.pitch?.toFixed(2) + '°' || 'N/A';
            document.getElementById('roll').textContent = data.roll?.toFixed(2) + '°' || 'N/A';
            document.getElementById('yaw').textContent = data.yaw?.toFixed(2) + '°' || 'N/A';
            if (data.lat !== undefined) document.getElementById('latitude').textContent = data.lat.toFixed(6);
            if (data.lon !== undefined) document.getElementById('longitude').textContent = data.lon.toFixed(6);
            if (data.alt !== undefined) document.getElementById('altitude').textContent = data.alt + ' m';
            if (data.speed !== undefined) document.getElementById('speed').textContent = data.speed + ' m/s';
            if (data.battery !== undefined) document.getElementById('battery').textContent = data.battery + '%';
            if (data.voltage !== undefined) document.getElementById('voltage').textContent = data.voltage + 'V';
            if (data.mode !== undefined) document.getElementById('mode').textContent = data.mode;
            if (data.flight_time !== undefined) {
                const t = data.flight_time;
                const h = String(Math.floor(t / 3600)).padStart(2, '0');
                const m = String(Math.floor((t % 3600) / 60)).padStart(2, '0');
                const s = String(t % 60).padStart(2, '0');
                document.getElementById('flight-time').textContent = `${h}:${m}:${s}`;
            }
            document.querySelector('.status-indicator').style.backgroundColor = 'limegreen';
        })
        .catch(error => {
            console.warn('Veri alınamadı:', error);
            [
                'pitch', 'roll', 'yaw',
                'latitude', 'longitude', 'altitude',
                'speed', 'battery', 'voltage', 'mode', 'flight-time'
            ].forEach(id => {
                const el = document.getElementById(id);
                if (el) el.textContent = 'Bağlantı yok';
            });
            document.querySelector('.status-indicator').style.backgroundColor = 'red';
        });
}

setInterval(updateTelemetry, 2000);

// Butonlar
document.getElementById("spray-on").addEventListener("click", () => {
    fetch("http://192.168.137.60:5000/spray/on", { method: "POST" });
});
document.getElementById("spray-off").addEventListener("click", () => {
    fetch("http://192.168.137.60:5000/spray/off", { method: "POST" });
});
document.getElementById("kapak-on").addEventListener("click", () => {
    fetch("http://192.168.137.60:5000/kapak/on", { method: "POST" });
});
document.getElementById("kapak-off").addEventListener("click", () => {
    fetch("http://192.168.137.60:5000/kapak/off", { method: "POST" });
});

// ARM butonu varsa bu şekilde
document.getElementById("arm-button").addEventListener("click", () => {
    fetch("http://192.168.137.60:5000/arm", { method: "POST" })
        .then(res => res.text())
        .then(data => console.log(data));
});
