# Geomagnetic Resilience Dashboard

🌍 **Real-time geomagnetic storm monitoring dashboard for Northeast New Jersey**

Monitor live space weather conditions using NOAA Space Weather Prediction Center (SWPC) data with real-time updates on solar wind, Kp index, and geomagnetically induced current (GIC) risks.

![Version](https://img.shields.io/badge/version-2.2.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## ✨ Features

### 📊 Real-Time NOAA Data Integration
- **Live NOAA SWPC Data** via CORS proxy solution
- **Dual Polling Strategy**:
  - Fast updates (60s): Solar wind speed, Bz field, proton density
  - Slow updates (10min): Kp index, storm scales, alerts
- **Automatic trend detection** for Kp and Bz parameters

### 🎯 NJ-Specific GIC Risk Assessment
- **Custom risk scoring algorithm** tailored for 40.8°N latitude
- **Regional vulnerability heatmap** covering Northeast Corridor
- **Infrastructure monitoring** for Bergen County and surrounding areas
- **Historical context** including 1989 Salem Nuclear Plant transformer failure

### 📈 Advanced Visualizations
- **Interactive storm visualization** with particle effects
- **Emergency response network graph**
- **Event timeline** with severity indicators
- **Multi-tab interface** for different analysis views

### ⚠️ Smart Alerting
- **Real-time storm alerts** when Kp ≥ 5
- **Severity-based color coding** (G1-G5 storm scales)
- **Infrastructure impact warnings** for power grids and GPS systems

---

## 🔍 The CORS Problem & Solution

### The Root Issue

**NOAA SWPC endpoints do NOT support CORS (Cross-Origin Resource Sharing).**

Browsers block direct `fetch()` calls to:
```
https://services.swpc.noaa.gov/products/*
```

This is **by design** for security - not a bug in the dashboard code.

### ✅ Our Solution: CORS Proxy

The dashboard uses **corsproxy.io** to bypass CORS restrictions:

```javascript
const CORS_PROXY = 'https://corsproxy.io/?';
const buildUrl = (endpoint) => {
  const baseUrl = `https://services.swpc.noaa.gov/products/${endpoint}`;
  return CORS_PROXY + encodeURIComponent(baseUrl);
};
```

**Key endpoints accessed:**
- `solar-wind/plasma-5-minute.json` - Solar wind speed, density, temperature
- `solar-wind/mag-5-minute.json` - Magnetic field (Bz, Bt)
- `noaa-planetary-k-index.json` - 3-hour Kp index
- `noaa-scales.json` - Current storm scale ratings
- `alerts.json` - Active space weather alerts

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ and npm/yarn
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/geomagnetic-dashboard.git
cd geomagnetic-dashboard

# Install dependencies
npm install

# Start development server
npm run dev
```

The dashboard will open at `http://localhost:3000`

### Build for Production

```bash
npm run build
npm run preview
```

---

## 🛠️ Configuration Options

### Change CORS Proxy

In `src/dashboard.jsx`, you can switch proxy providers:

```javascript
// Option 1: corsproxy.io (default)
const CORS_PROXY = 'https://corsproxy.io/?';

// Option 2: allorigins.win
const CORS_PROXY = 'https://api.allorigins.win/raw?url=';

// Option 3: Your own backend proxy
const USE_CORS_PROXY = false; // Set to false if using backend
```

### Adjust Polling Intervals

```javascript
// In MainDashboard component
const spaceWeather = useSpaceWeatherData(
  60000,   // Fast polling: 60 seconds (solar wind, Bz)
  600000   // Slow polling: 10 minutes (Kp, alerts)
);
```

---

## 📊 Data Sources & Accuracy

### NOAA SWPC Endpoints
| Data Type | Update Frequency | Delay | Source Instrument |
|-----------|-----------------|-------|-------------------|
| Solar Wind (V, ρ, T) | ~5 minutes | 15-60 min | DSCOVR @ L1 |
| Magnetic Field (Bz, Bt) | ~5 minutes | 15-60 min | DSCOVR @ L1 |
| Kp Index | 3 hours | 3-6 hours | Global magnetometer network |
| Storm Scales | Real-time | Varies | NOAA analysis |
| Alerts | As issued | Minutes | SWPC forecasters |

### ⚠️ Important Caveats
- **Kp Index**: 3-hour average updated every 3 hours—not real-time storm intensity
- **L1 Delay**: Solar wind measured ~1.5M km away; 15-60 min propagation to Earth
- **Local Variation**: Actual GIC at your location may differ from model estimates
- **Historical Context**: 1989 Salem transformer failure shown for reference, not prediction
- **Polling**: Not continuous monitoring—fast data every 60s, slow data every 10min

---

## 🎯 NJ GIC Risk Algorithm

Custom heuristic scoring for Northeast NJ (40.8°N):

```javascript
Score = (Kp/9 × 60) + |Bz| × 1.5 + (V-500)/20 + (ρ-10)

Risk Levels:
- EXTREME: 80-100 (Critical infrastructure stress)
- HIGH: 60-79 (Significant GIC activity)
- ELEVATED: 40-59 (Monitor conditions)
- MODERATE: 0-39 (Normal operations)
```

**Factors:**
- Kp index (60% weight) - Global geomagnetic activity
- Southward Bz (20% weight) - Reconnection efficiency
- Solar wind speed (10% weight) - Dynamic pressure
- Proton density (10% weight) - Mass flux

---

## 🏭 Northeast NJ Infrastructure Context

### High-Risk Areas
| Region | Risk Score | Key Infrastructure |
|--------|-----------|-------------------|
| NYC Metro | 90% | Consolidated Edison grid |
| North NJ | 88% | Bergen/Passaic/Essex counties |
| Central NJ | 82% | Union/Somerset/Middlesex |
| South NJ | 78% | Salem Nuclear Plant (500kV) |

### Vulnerability Factors
- **Geologic**: Piedmont rock formation → high resistivity
- **Latitude**: 40.8°N in moderate-to-high GMD zone
- **Tectonic**: Complex structures amplify geoelectric fields
- **Infrastructure**: 70%+ transformers >25 years old

### 1989 Historical Event
**March 13, 1989**: Salem Nuclear Plant transformer failure
- 500kV transformer damaged by GIC during Quebec blackout storm
- Kp=9, severe geomagnetic conditions
- Demonstrates NJ vulnerability to extreme events

---

## 🕸️ Emergency Response Features

### Community Network Graph
- Bergen County Emergency Management (hub)
- Hackensack University Medical Center
- PSEG Grid Operations
- Amateur Radio Networks
- Food/water supply chains
- Municipal coordination centers

### Timeline View
- Real-time event tracking
- Historical storm comparisons
- Severity classifications
- Infrastructure impact logs

---

## 🔧 Advanced Deployment Options

### Option 1: Public CORS Proxy (Current)
✅ **Pros**: Instant deployment, zero server setup
⚠️ **Cons**: Rate limits, third-party dependency

**Recommended for**: Development, testing, personal use

### Option 2: Self-Hosted Backend Proxy
Create `proxy.js`:

```javascript
const express = require('express');
const cors = require('cors');
const fetch = require('node-fetch');

const app = express();
app.use(cors());

app.get('/api/swpc/:endpoint(*)', async (req, res) => {
  const endpoint = req.params.endpoint;
  const url = `https://services.swpc.noaa.gov/products/${endpoint}`;

  try {
    const response = await fetch(url);
    const data = await response.json();
    res.json(data);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.listen(3001, () => console.log('CORS proxy on port 3001'));
```

Update dashboard:
```javascript
const USE_CORS_PROXY = false;
const PROXY_BASE = 'http://localhost:3001/api/swpc';
```

**Recommended for**: Production deployments, high-traffic use

### Option 3: Serverless Functions (Vercel/Netlify)
Create `api/swpc.js`:

```javascript
export default async function handler(req, res) {
  const { endpoint } = req.query;
  const url = `https://services.swpc.noaa.gov/products/${endpoint}`;

  const response = await fetch(url);
  const data = await response.json();

  res.setHeader('Access-Control-Allow-Origin', '*');
  res.json(data);
}
```

**Recommended for**: Scalable production, zero server management

---

## 📱 Browser Compatibility

| Browser | Minimum Version | Status |
|---------|----------------|--------|
| Chrome | 90+ | ✅ Fully supported |
| Firefox | 88+ | ✅ Fully supported |
| Safari | 14+ | ✅ Fully supported |
| Edge | 90+ | ✅ Fully supported |

**Requirements:**
- JavaScript enabled
- CSS Grid support
- Fetch API support
- ES6+ features

---

## 🧪 Testing & Verification

### After Implementation

1. **Open browser DevTools** (F12)
2. **Go to Console tab**
3. **Refresh dashboard**
4. **Check for successful fetch logs**
5. **Verify Network tab** - should see 200 OK responses

### Expected Outputs
```
✓ Kp Index: 4.3 (real from NOAA)
✓ Solar Wind: 425 km/s (real)
✓ Bz Field: -2.1 nT (real)
✓ Timestamps: current hour
✓ No "—" placeholders
```

### Troubleshooting
❌ **CORS Error in Console**
→ Check CORS_PROXY URL is correct
→ Verify proxy service is online

❌ **Data shows "—" placeholders**
→ Check NOAA endpoints are responding
→ Verify internet connection
→ Check browser console for errors

❌ **Slow updates**
→ This is normal - fast updates every 60s, slow every 10min
→ NOAA data has inherent delays (see Data Sources table)

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -m 'Add improvement'`)
4. Push to branch (`git push origin feature/improvement`)
5. Open a Pull Request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **NOAA Space Weather Prediction Center** - Real-time data
- **USGS Geomagnetic Program** - Research and historical data
- **DOE OE-417** - Infrastructure impact reports
- **Academic Research** - GIC vulnerability studies

---

## 📞 Support & Contact

**Issues**: [GitHub Issues](https://github.com/yourusername/geomagnetic-dashboard/issues)
**Documentation**: This README
**NOAA SWPC**: https://www.swpc.noaa.gov/

---

## 🔗 Related Resources

- [NOAA Space Weather Scales](https://www.swpc.noaa.gov/noaa-scales-explanation)
- [USGS Geomagnetism Program](https://www.usgs.gov/natural-hazards/geomagnetism)
- [NERC GMD Standards](https://www.nerc.com/pa/Stand/Pages/Project-2013-03-Geomagnetic-Disturbance-Mitigation.aspx)
- [PSEG Outage Map](https://nj.pseg.com/outages)

---

**Built with ❤️ for Northeast New Jersey resilience**

*Stay informed. Stay prepared. Monitor space weather in real-time.*
