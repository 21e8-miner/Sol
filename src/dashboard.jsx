import React, { useState, useEffect, useMemo } from 'react';

// NOAA SWPC Real-Time Data Endpoints
// Note: NOAA servers don't support CORS, so we use a proxy for browser access
const USE_CORS_PROXY = true; // Set to false if using your own backend proxy

const CORS_PROXY = USE_CORS_PROXY ? 'https://corsproxy.io/?' : '';

const buildUrl = (endpoint) => {
  const baseUrl = `https://services.swpc.noaa.gov/products/${endpoint}`;
  return USE_CORS_PROXY ? CORS_PROXY + encodeURIComponent(baseUrl) : baseUrl;
};

const SWPC_ENDPOINTS = {
  plasma: buildUrl('solar-wind/plasma-5-minute.json'),
  mag: buildUrl('solar-wind/mag-5-minute.json'),
  kp: buildUrl('noaa-planetary-k-index.json'),
  scales: buildUrl('noaa-scales.json'),
  alerts: buildUrl('alerts.json'),
};

const safeParse = (val) => {
  const num = parseFloat(val);
  return Number.isFinite(num) ? num : null;
};

function mapKpToStormScale(kp) {
  if (kp == null) return null;
  if (kp >= 9.0) return { level: 'G5', name: 'Extreme' };
  if (kp >= 8.0) return { level: 'G4', name: 'Severe' };
  if (kp >= 7.0) return { level: 'G3', name: 'Strong' };
  if (kp >= 6.0) return { level: 'G2', name: 'Moderate' };
  if (kp >= 5.0) return { level: 'G1', name: 'Minor' };
  return { level: 'G0', name: 'Quiet' };
}

function clamp(val, min, max) {
  return Math.min(max, Math.max(min, val));
}

function computeTrend(values, eps = 0.5) {
  if (!values || values.length < 3) return null;
  const first = values[0];
  const last = values[values.length - 1];
  const delta = last - first;
  if (!isFinite(delta)) return null;
  if (Math.abs(delta) < eps) return 'steady';
  return delta > 0 ? 'rising' : 'falling';
}

// NJ-Specific GIC Risk Scoring Algorithm
function computeNjRiskScore({ kp, bz, v, n }) {
  if (kp == null && bz == null && v == null && n == null) return null;
  const safeKp = kp ?? 0;
  const safeBz = bz ?? 0;
  const safeV = v ?? 0;
  const safeN = n ?? 0;

  let score = (safeKp / 9) * 60;

  if (safeBz < 0) {
    score += Math.min(20, Math.abs(safeBz) * 1.5);
  }

  if (safeV > 500) {
    score += Math.min(10, (safeV - 500) / 20);
  }

  if (safeN > 10) {
    score += Math.min(10, safeN - 10);
  }

  return Math.round(clamp(score, 0, 100));
}

function labelNjRisk(score) {
  if (score == null) return { label: 'Unknown', color: 'text-slate-400' };
  if (score >= 80) return { label: 'EXTREME', color: 'text-red-400' };
  if (score >= 60) return { label: 'HIGH', color: 'text-orange-400' };
  if (score >= 40) return { label: 'ELEVATED', color: 'text-yellow-400' };
  return { label: 'MODERATE', color: 'text-green-400' };
}

function summarizeAlert(alerts) {
  if (!Array.isArray(alerts) || !alerts.length) return null;
  const interesting = alerts.find(a =>
    typeof a.message === 'string' &&
    (a.message.includes('Geomagnetic') || a.message.includes('K-index'))
  ) || alerts[0];

  if (!interesting || typeof interesting.message !== 'string') return null;

  const lines = interesting.message.split('\n').map(l => l.trim()).filter(Boolean);
  const headline = lines.find(l => l.startsWith('ALERT:') || l.startsWith('WATCH:') || l.startsWith('WARNING:'));
  const valid = lines.find(l => l.startsWith('Valid From:') || l.startsWith('Threshold Reached:'));

  return {
    productId: interesting.product_id,
    issued: interesting.issue_datetime,
    headline: headline || 'Space weather alert in effect',
    window: valid || null,
  };
}

// Split fast/slow polling hook for optimal performance
function useSpaceWeatherData(fastMs = 60000, slowMs = 600000) {
  const [data, setData] = useState({
    loading: true,
    error: null,
    lastUpdated: null,
    lastFastUpdate: null,
    lastSlowUpdate: null,
    kp: null,
    kpTime: null,
    solarWindSpeed: null,
    protonDensity: null,
    protonTemp: null,
    bz: null,
    bt: null,
    stormScale: null,
    noaaGScale: null,
    noaaGText: null,
    latestAlert: null,
    history: [],
    kpTrend: null,
    bzTrend: null,
    njRiskScore: null,
  });

  // Fast loop: plasma + mag (near real-time, ~5min NOAA cadence)
  useEffect(() => {
    let cancelled = false;
    const MAX_HISTORY = 24;

    const fetchFast = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);

        const [plasmaRes, magRes] = await Promise.all([
          fetch(SWPC_ENDPOINTS.plasma, { signal: controller.signal }),
          fetch(SWPC_ENDPOINTS.mag, { signal: controller.signal }),
        ]);

        clearTimeout(timeoutId);
        if (!plasmaRes.ok || !magRes.ok) throw new Error('SWPC fast endpoints unavailable');

        const [plasmaJson, magJson] = await Promise.all([
          plasmaRes.json(),
          magRes.json(),
        ]);

        const plasmaRows = Array.isArray(plasmaJson) ? plasmaJson : [];
        const magRows = Array.isArray(magJson) ? magJson : [];

        const latestPlasma = plasmaRows.length > 1 ? plasmaRows[plasmaRows.length - 1] : null;
        const latestMag = magRows.length > 1 ? magRows[magRows.length - 1] : null;

        const plasmaSpeed = latestPlasma ? safeParse(latestPlasma[2]) : null;
        const plasmaDensity = latestPlasma ? safeParse(latestPlasma[1]) : null;
        const plasmaTemp = latestPlasma ? safeParse(latestPlasma[3]) : null;
        const bz = latestMag ? safeParse(latestMag[3]) : null;
        const bt = latestMag ? safeParse(latestMag[6]) : null;

        const now = new Date();

        setData(prev => {
          if (cancelled) return prev;

          const newPoint = {
            t: now.toISOString(),
            kp: prev.kp,
            bz,
            v: plasmaSpeed,
            n: plasmaDensity,
          };

          const history = [...(prev.history || []), newPoint].slice(-MAX_HISTORY);
          const kpSeries = history.map(h => h.kp).filter(v => v != null);
          const bzSeries = history.map(h => h.bz).filter(v => v != null);

          const kpTrend = computeTrend(kpSeries, 0.3);
          const bzTrend = computeTrend(bzSeries, 0.5);

          const njRiskScore = computeNjRiskScore({
            kp: prev.kp,
            bz,
            v: plasmaSpeed,
            n: plasmaDensity,
          });

          return {
            ...prev,
            loading: prev.loading && prev.kp == null,
            lastUpdated: now,
            lastFastUpdate: now,
            solarWindSpeed: plasmaSpeed,
            protonDensity: plasmaDensity,
            protonTemp: plasmaTemp,
            bz,
            bt,
            history,
            kpTrend,
            bzTrend,
            njRiskScore,
          };
        });
      } catch (err) {
        if (cancelled) return;
        setData(prev => ({
          ...prev,
          loading: false,
          error:
            err?.name === 'AbortError'
              ? 'SWPC fast request timed out'
              : (prev.error ?? err?.message ?? 'Failed to fetch fast SWPC data'),
        }));
      }
    };

    fetchFast();
    const id = setInterval(fetchFast, fastMs);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [fastMs]);

  // Slow loop: Kp + scales + alerts (3-hour official cadence)
  useEffect(() => {
    let cancelled = false;

    const fetchSlow = async () => {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000);

        const [kpRes, scalesRes, alertsRes] = await Promise.all([
          fetch(SWPC_ENDPOINTS.kp, { signal: controller.signal }),
          fetch(SWPC_ENDPOINTS.scales, { signal: controller.signal }),
          fetch(SWPC_ENDPOINTS.alerts, { signal: controller.signal }),
        ]);

        clearTimeout(timeoutId);
        if (!kpRes.ok) throw new Error('SWPC Kp endpoint unavailable');

        const [kpJson, scalesJson, alertsJson] = await Promise.all([
          kpRes.json(),
          scalesRes.ok ? scalesRes.json() : null,
          alertsRes.ok ? alertsRes.json() : null,
        ]);

        const kpRows = Array.isArray(kpJson) ? kpJson : [];
        const latestKp = kpRows.length > 1 ? kpRows[kpRows.length - 1] : null;
        const kpTime = latestKp?.[0] ?? null;
        const kpVal = latestKp ? safeParse(latestKp[1]) : null;

        const stormInfo = mapKpToStormScale(kpVal);

        let noaaGScale = null;
        let noaaGText = null;
        if (scalesJson && typeof scalesJson === 'object' && scalesJson['0']?.G) {
          const g = scalesJson['0'].G;
          noaaGScale = g.Scale != null ? `G${g.Scale}` : null;
          noaaGText = g.Text ?? null;
        }

        const latestAlert = summarizeAlert(alertsJson);

        const now = new Date();

        setData(prev => {
          if (cancelled) return prev;

          const updatedStorm = mapKpToStormScale(kpVal);
          const njRiskScore = computeNjRiskScore({
            kp: kpVal,
            bz: prev.bz,
            v: prev.solarWindSpeed,
            n: prev.protonDensity,
          });

          const history = (prev.history || []).map(h => ({
            ...h,
            kp: h.kp ?? kpVal,
          }));

          const kpSeries = history.map(h => h.kp).filter(v => v != null);
          const kpTrend = computeTrend(kpSeries, 0.3);

          return {
            ...prev,
            loading: false,
            lastSlowUpdate: now,
            error: prev.error,
            kp: kpVal,
            kpTime,
            stormScale: updatedStorm,
            noaaGScale,
            noaaGText,
            latestAlert,
            history,
            kpTrend,
            njRiskScore,
          };
        });
      } catch (err) {
        if (cancelled) return;
        setData(prev => ({
          ...prev,
          loading: false,
          error:
            err?.name === 'AbortError'
              ? 'SWPC slow request timed out'
              : (prev.error ?? err?.message ?? 'Failed to fetch slow SWPC data'),
        }));
      }
    };

    fetchSlow();
    const id = setInterval(fetchSlow, slowMs);

    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [slowMs]);

  return data;
}

// Storm Visualization Component with trend indicators
const StormVisualization = ({ spaceWeather }) => {
  const [rotation, setRotation] = useState(0);
  const [particleIntensity, setParticleIntensity] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setRotation(prev => (prev + 2) % 360);
      setParticleIntensity(prev => (prev + 0.05) % (Math.PI * 2));
    }, 50);
    return () => clearInterval(interval);
  }, []);

  const swSpeed = spaceWeather?.solarWindSpeed;
  const bz = spaceWeather?.bz;
  const density = spaceWeather?.protonDensity;
  const kp = spaceWeather?.kp;

  const swLabel = swSpeed != null ? `${swSpeed.toFixed(0)} km/s` : '—';
  const bzLabel = bz != null ? `${bz.toFixed(1)} nT` : '—';
  const densityLabel = density != null ? `${density.toFixed(1)} p/cm³` : '—';
  const kpLabel = kp != null ? kp.toFixed(1) : '—';

  const particleCount = kp != null ? Math.min(30, Math.max(8, Math.floor(kp * 3))) : 20;

  const kpTrendIcon = spaceWeather?.kpTrend === 'rising' ? '↗' :
                      spaceWeather?.kpTrend === 'falling' ? '↘' :
                      spaceWeather?.kpTrend === 'steady' ? '→' : '';

  const bzTrendIcon = spaceWeather?.bzTrend === 'rising' ? '↗' :
                      spaceWeather?.bzTrend === 'falling' ? '↘' :
                      spaceWeather?.bzTrend === 'steady' ? '→' : '';

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h3 className="text-xl font-semibold text-white mb-4">Solar Wind Impact - Live NOAA Data</h3>
      {spaceWeather?.loading && (
        <div className="text-slate-400 text-sm mb-2">Loading real-time data from SWPC...</div>
      )}
      {spaceWeather?.error && (
        <div className="text-red-400 text-sm mb-2">⚠ {spaceWeather.error}</div>
      )}
      <div className="relative w-full h-64 bg-slate-900 rounded-lg overflow-hidden">
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="w-24 h-24 rounded-full bg-gradient-to-br from-blue-500 to-green-500 shadow-lg shadow-blue-500/50" />
          <div
            className={`absolute inset-0 rounded-full border-4 ${
              bz != null && bz < -10 ? 'border-red-400' : 'border-blue-400'
            } opacity-50 animate-ping`}
            style={{ animationDuration: kp != null && kp > 6 ? '2s' : '3s' }}
          />
          <div className="absolute top-6 right-4 w-2 h-2 bg-yellow-400 rounded-full animate-pulse" title="Northeast NJ (40.8°N)" />
        </div>

        {[...Array(particleCount)].map((_, i) => {
          const intensity = Math.sin(particleIntensity + i * 0.3);
          return (
            <div
              key={i}
              className={`absolute w-3 h-3 rounded-full ${
                kp != null && kp >= 7 ? 'bg-red-400' : 'bg-yellow-400'
              }`}
              style={{
                top: `${20 + Math.sin(rotation * 0.05 + i) * 30}%`,
                left: `${(rotation * 1.5 + i * 18) % 100}%`,
                opacity: 0.6 + intensity * 0.4,
                boxShadow: `0 0 ${8 + intensity * 4}px ${
                  kp != null && kp >= 7
                    ? 'rgba(248, 113, 113, 0.8)'
                    : 'rgba(251, 191, 36, 0.8)'
                }`,
              }}
            />
          );
        })}

        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-40 h-40 rounded-full border-2 border-purple-400 opacity-30"
          style={{
            transform: `translate(-50%, -50%) scale(${
              kp != null && kp > 6 ? 0.85 : 0.9
            }, ${kp != null && kp > 6 ? 1.15 : 1.1})`,
          }}
        />
        <div
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 rounded-full border-2 border-purple-500 opacity-15"
          style={{
            transform: `translate(-50%, -50%) scale(${
              kp != null && kp > 6 ? 0.8 : 0.85
            }, ${kp != null && kp > 6 ? 1.2 : 1.15})`,
          }}
        />

        {kp != null && kp >= 5 && (
          <div className="absolute bottom-4 left-4 text-xs text-red-400 font-mono bg-slate-800/80 px-2 py-1 rounded animate-pulse">
            GIC: ACTIVE
          </div>
        )}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-slate-400">Solar wind (L1):</span>
          <span
            className={`font-semibold ml-2 ${
              swSpeed != null && swSpeed > 600 ? 'text-red-400' : 'text-yellow-400'
            }`}
          >
            {swLabel}
          </span>
        </div>
        <div>
          <span className="text-slate-400">Bz (IMF):</span>
          <span
            className={`font-semibold ml-2 ${
              bz != null && bz < 0 ? 'text-red-400' : 'text-green-400'
            }`}
          >
            {bzLabel} {bzTrendIcon}
          </span>
        </div>
        <div>
          <span className="text-slate-400">Proton density:</span>
          <span className="text-orange-400 font-semibold ml-2">{densityLabel}</span>
        </div>
        <div>
          <span className="text-slate-400">Kp (3-hr avg):</span>
          <span
            className={`font-semibold ml-2 ${
              kp != null && kp >= 7
                ? 'text-red-400'
                : kp != null && kp >= 5
                ? 'text-orange-400'
                : 'text-green-400'
            }`}
          >
            {kpLabel} {kpTrendIcon}
          </span>
        </div>
      </div>
      <div className="mt-2 text-xs text-slate-500">
        Fast (SW/Bz): {spaceWeather?.lastFastUpdate?.toLocaleTimeString() ?? '—'} •
        Slow (Kp): {spaceWeather?.lastSlowUpdate?.toLocaleTimeString() ?? '—'}
      </div>
    </div>
  );
};

// Risk Heatmap Component (static geologic/infrastructure risk)
const RiskHeatmap = () => {
  const regions = [
    { name: 'North NJ', risk: 88, color: 'bg-red-600', detail: 'Bergen, Passaic, Essex Counties' },
    { name: 'Central NJ', risk: 82, color: 'bg-red-500', detail: 'Union, Somerset, Middlesex' },
    { name: 'Shore', risk: 65, color: 'bg-orange-500', detail: 'Monmouth, Ocean Counties' },
    { name: 'South NJ', risk: 78, color: 'bg-orange-600', detail: 'Salem Nuclear Plant area' },
    { name: 'NYC Metro', risk: 90, color: 'bg-red-600', detail: 'High pop density + grid' },
    { name: 'Hudson Valley', risk: 75, color: 'bg-orange-500', detail: 'Rockland, Westchester' },
    { name: 'Long Island', risk: 70, color: 'bg-orange-500', detail: 'LIPA grid system' },
    { name: 'Philly Metro', risk: 72, color: 'bg-orange-500', detail: 'PECO territory' },
  ];

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h3 className="text-xl font-semibold text-white mb-4">
        Regional GIC Risk Assessment - Northeast Corridor
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
        {regions.map((region, idx) => (
          <div
            key={idx}
            className={`${region.color} rounded p-3 text-white text-center transition-all hover:scale-105 cursor-pointer group relative`}
          >
            <div className="text-xs font-semibold">{region.name}</div>
            <div className="text-lg font-bold">{region.risk}%</div>
            <div className="absolute hidden group-hover:block bg-slate-900 text-xs p-2 rounded -top-12 left-1/2 -translate-x-1/2 whitespace-nowrap z-10 border border-slate-600">
              {region.detail}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 flex justify-between text-xs text-slate-400">
        <span>🟢 Low (&lt;50%)</span>
        <span>🟡 Moderate (50-70%)</span>
        <span>🟠 High (70-85%)</span>
        <span>🔴 Extreme (&gt;85%)</span>
      </div>
      <div className="mt-4 p-3 bg-slate-900/50 rounded border border-slate-700">
        <div className="text-slate-300 text-sm mb-2">
          <strong className="text-orange-400">Geologic Risk Factors:</strong>
        </div>
        <ul className="text-slate-400 text-xs space-y-1">
          <li>• Piedmont rock formation in NE NJ increases resistivity and GIC vulnerability</li>
          <li>• Latitude 40.8°N in moderate-to-high geomagnetic disturbance zone</li>
          <li>• Complex tectonic structures amplify geoelectric field intensity</li>
          <li>• Aging transformer infrastructure (&gt;25 years old in many substations)</li>
        </ul>
      </div>
    </div>
  );
};

// Timeline View Component
const TimelineView = () => {
  const events = [
    { time: 'Nov 11 02:00 UTC', event: 'X5.1 solar flare detected on Sun', severity: 'high', detail: 'Strongest flare in months' },
    { time: 'Nov 11 14:30 UTC', event: 'CME departure confirmed by SOHO', severity: 'high', detail: 'Full halo CME, Earth-directed' },
    { time: 'Nov 12 01:20 UTC', event: 'G4 (Severe) storm levels reached', severity: 'high', detail: 'Kp=8 at peak' },
    { time: 'Nov 12 03:45 UTC', event: 'Power grid voltage fluctuations detected', severity: 'medium', detail: 'Multiple utilities report GIC' },
    { time: 'Nov 12 05:20 UTC', event: 'GPS accuracy degraded 15-30m', severity: 'medium', detail: 'Aviation notices issued' },
    { time: 'Nov 12 06:00 UTC', event: 'Aurora visible from New Jersey', severity: 'low', detail: 'Reports from Bergen County' },
    { time: 'HISTORICAL', event: 'Mar 13, 1989: Salem Nuclear Plant transformer failure', severity: 'high', detail: '500kV transformer damaged by GIC' },
  ];

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'high': return 'bg-red-500';
      case 'medium': return 'bg-orange-500';
      case 'low': return 'bg-green-500';
      default: return 'bg-slate-500';
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h3 className="text-xl font-semibold text-white mb-4">
        Event Timeline - Current Storm & Historical Context
      </h3>
      <div className="space-y-4">
        {events.map((evt, idx) => (
          <div key={idx} className="flex items-start gap-4">
            <div className="text-slate-400 text-xs font-mono w-32 flex-shrink-0">{evt.time}</div>
            <div className={`w-3 h-3 rounded-full ${getSeverityColor(evt.severity)} mt-1 flex-shrink-0`} />
            <div className="flex-1">
              <div className="text-slate-200 font-medium">{evt.event}</div>
              <div className="text-slate-400 text-sm">{evt.detail}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-6 p-4 bg-slate-900/50 rounded border border-slate-700">
        <div className="text-slate-300 text-sm">
          <strong className="text-orange-400">Data Sources:</strong> NOAA Space Weather Prediction Center (SWPC),
          USGS Geoelectric Field Monitoring, DOE OE-417 Incident Reports, Academic Research (PLOS One 2025)
        </div>
      </div>
    </div>
  );
};

// Network Graph Component
const NetworkGraph = () => {
  const [hoveredNode, setHoveredNode] = useState(null);

  const nodes = [
    { id: 1, x: 50, y: 20, name: 'Emergency Mgmt (Bergen Co.)', type: 'hub', connections: 12, critical: true },
    { id: 2, x: 25, y: 35, name: 'Medical (Hackensack UMC)', type: 'medical', connections: 8, critical: true },
    { id: 3, x: 75, y: 35, name: 'PSEG Grid Ops', type: 'power', connections: 10, critical: true },
    { id: 4, x: 15, y: 55, name: 'Amateur Radio Net', type: 'comms', connections: 6, critical: false },
    { id: 5, x: 50, y: 50, name: 'Community Hub (Teaneck)', type: 'hub', connections: 9, critical: false },
    { id: 6, x: 85, y: 55, name: 'Tech Support (Rutgers)', type: 'tech', connections: 7, critical: false },
    { id: 7, x: 30, y: 70, name: 'Food Bank Network', type: 'supply', connections: 5, critical: false },
    { id: 8, x: 70, y: 70, name: 'Water/Utilities', type: 'utilities', connections: 6, critical: true },
    { id: 9, x: 50, y: 85, name: 'EOC Coordination', type: 'hub', connections: 11, critical: true },
  ];

  const getNodeColor = (type) => {
    switch (type) {
      case 'hub': return 'bg-blue-500';
      case 'medical': return 'bg-red-400';
      case 'tech': return 'bg-purple-500';
      case 'supply': return 'bg-green-500';
      case 'comms': return 'bg-yellow-500';
      case 'power': return 'bg-orange-500';
      case 'utilities': return 'bg-cyan-500';
      default: return 'bg-slate-500';
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h3 className="text-xl font-semibold text-white mb-4">Northeast NJ Emergency Response Network</h3>
      <div className="relative w-full h-96 bg-slate-900 rounded-lg overflow-hidden">
        <svg className="absolute inset-0 w-full h-full">
          {nodes.map(node =>
            nodes
              .filter(n => n.id > node.id && (node.critical || n.critical))
              .map(target => (
                <line
                  key={`${node.id}-${target.id}`}
                  x1={`${node.x}%`}
                  y1={`${node.y}%`}
                  x2={`${target.x}%`}
                  y2={`${target.y}%`}
                  stroke={node.critical && target.critical ? '#f59e0b' : '#475569'}
                  strokeWidth={node.critical && target.critical ? '2' : '1'}
                  opacity={node.critical && target.critical ? '0.6' : '0.3'}
                />
              )),
          )}
        </svg>

        {nodes.map(node => (
          <div
            key={node.id}
            className={`absolute ${getNodeColor(node.type)} rounded-full cursor-pointer transition-all ${
              node.critical ? 'ring-2 ring-orange-400' : ''
            }`}
            style={{
              left: `${node.x}%`,
              top: `${node.y}%`,
              width: hoveredNode === node.id ? '56px' : node.critical ? '40px' : '32px',
              height: hoveredNode === node.id ? '56px' : node.critical ? '40px' : '32px',
              transform: 'translate(-50%, -50%)',
              boxShadow:
                hoveredNode === node.id
                  ? '0 0 24px rgba(59, 130, 246, 0.6)'
                  : node.critical
                  ? '0 0 12px rgba(251, 146, 60, 0.4)'
                  : 'none',
              zIndex: hoveredNode === node.id ? 20 : node.critical ? 15 : 10,
            }}
            onMouseEnter={() => setHoveredNode(node.id)}
            onMouseLeave={() => setHoveredNode(null)}
          >
            {hoveredNode === node.id && (
              <div className="absolute top-full mt-2 left-1/2 -translate-x-1/2 bg-slate-700 text-white text-xs px-3 py-2 rounded whitespace-nowrap z-30 border border-slate-600">
                <div className="font-semibold">{node.name}</div>
                <div className="text-slate-400">{node.connections} connections</div>
                {node.critical && <div className="text-orange-400">⚡ Critical Node</div>}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-slate-400">Coordination Hub</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-400" />
          <span className="text-slate-400">Medical</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-orange-500" />
          <span className="text-slate-400">Power Grid</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-yellow-500" />
          <span className="text-slate-400">Communications</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-slate-400">Supply Chain</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-purple-500" />
          <span className="text-slate-400">Tech Support</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-cyan-500" />
          <span className="text-slate-400">Utilities</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full ring-2 ring-orange-400" />
          <span className="text-slate-400">Critical Node</span>
        </div>
      </div>
      <div className="mt-4 p-3 bg-slate-900/50 rounded border border-slate-700">
        <div className="text-slate-300 text-sm">
          <strong className="text-blue-400">Network Status:</strong> Based on Bergen County OEM structure and
          regional PSEG coordination protocols. Critical nodes are essential for storm response and recovery operations.
        </div>
      </div>
    </div>
  );
};

// Main Dashboard Component
const MainDashboard = () => {
  const [activeTab, setActiveTab] = useState('overview');
  const [stormAlert, setStormAlert] = useState(true);

  // Split fast/slow polling: 1min for SW/Bz, 10min for Kp/alerts
  const spaceWeather = useSpaceWeatherData(60000, 600000);

  const lastUpdateDisplay = useMemo(() => {
    if (!spaceWeather.lastUpdated) return '—';
    return spaceWeather.lastUpdated.toLocaleTimeString();
  }, [spaceWeather.lastUpdated]);

  const tabs = [
    { id: 'overview', label: 'Overview', icon: '🌍' },
    { id: 'storm', label: 'Live Data', icon: '⚡' },
    { id: 'risk', label: 'Risk Analysis', icon: '🔥' },
    { id: 'timeline', label: 'Event Timeline', icon: '📊' },
    { id: 'network', label: 'Community Network', icon: '🕸️' },
  ];

  const kpDisplay = spaceWeather.kp != null ? spaceWeather.kp.toFixed(1) : '—';
  const stormLevelDisplay = spaceWeather.stormScale?.level ?? spaceWeather.noaaGScale ?? 'G0';
  const stormNameDisplay = spaceWeather.stormScale?.name ?? spaceWeather.noaaGText ?? 'Quiet';
  const swSpeedDisplay = spaceWeather.solarWindSpeed != null ? `${spaceWeather.solarWindSpeed.toFixed(0)} km/s` : '—';
  const bzDisplay = spaceWeather.bz != null ? `${spaceWeather.bz.toFixed(1)} nT` : '—';
  const densityDisplay = spaceWeather.protonDensity != null ? `${spaceWeather.protonDensity.toFixed(1)} p/cm³` : '—';

  const isStormActive = spaceWeather.kp != null && spaceWeather.kp >= 5;
  const isHighStorm = spaceWeather.kp != null && spaceWeather.kp >= 7;
  const isSevereStorm = spaceWeather.kp != null && spaceWeather.kp >= 8;

  const njRiskScore = spaceWeather.njRiskScore;
  const njRisk = labelNjRisk(njRiskScore);

  const kpTrendLabel =
    spaceWeather.kpTrend === 'rising' ? '↗ Kp rising' :
    spaceWeather.kpTrend === 'falling' ? '↘ Kp falling' :
    spaceWeather.kpTrend === 'steady' ? '→ Kp steady' : '';

  const bzTrendLabel =
    spaceWeather.bzTrend === 'rising' ? 'Bz → N' :
    spaceWeather.bzTrend === 'falling' ? 'Bz → S' :
    spaceWeather.bzTrend === 'steady' ? 'Bz steady' : '';

  return (
    <div className="min-h-screen bg-slate-900 p-4">
      {/* Header */}
      <div className="mb-6">
        <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">Geomagnetic Resilience Dashboard</h1>
            <p className="text-slate-400">
              Northeast New Jersey • Live NOAA SWPC • Last: {lastUpdateDisplay}
            </p>
            {spaceWeather.error && (
              <p className="text-xs text-red-400 mt-1">⚠ {spaceWeather.error}</p>
            )}
          </div>

          {stormAlert && isStormActive && (
            <div
              className={`${
                isSevereStorm ? 'bg-red-600' : isHighStorm ? 'bg-orange-600' : 'bg-yellow-600'
              } border ${
                isSevereStorm ? 'border-red-400' : 'border-orange-400'
              } rounded-lg p-4 w-full lg:w-auto`}
            >
              <div className="flex items-center gap-3">
                <div className="text-2xl animate-pulse">⚠️</div>
                <div className="flex-1">
                  <div className="text-white font-semibold">
                    {stormLevelDisplay} ({stormNameDisplay}) Storm Active
                  </div>
                  <div className={`${isSevereStorm ? 'text-red-200' : 'text-orange-200'} text-sm`}>
                    Kp: {kpDisplay} • Wind: {swSpeedDisplay} • Bz: {bzDisplay} • Risk: {njRiskScore ?? '—'}/100
                  </div>
                  {spaceWeather.latestAlert && (
                    <div className="text-xs text-red-100 mt-1">
                      {spaceWeather.latestAlert.headline}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => setStormAlert(false)}
                  className={`${
                    isSevereStorm ? 'text-red-200 hover:text-white' : 'text-orange-200 hover:text-white'
                  } text-2xl`}
                >
                  ×
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="mb-6">
        <div className="flex flex-wrap gap-1 bg-slate-800 p-1 rounded-lg">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                activeTab === tab.id
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              <span>{tab.icon}</span>
              <span className="text-sm lg:text-base">{tab.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Quick Stats with enhanced Kp labeling */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div
          className={`bg-slate-800 rounded-lg p-4 ${
            isSevereStorm ? 'border-2 border-red-500' : isHighStorm ? 'border-2 border-orange-500' : ''
          }`}
        >
          <div className="text-slate-400 text-sm">Kp Index (3-hr NOAA)</div>
          <div
            className={`text-2xl font-bold ${
              isSevereStorm ? 'text-red-400' : isHighStorm ? 'text-orange-400' : isStormActive ? 'text-yellow-400' : 'text-green-400'
            }`}
          >
            {spaceWeather.loading ? '...' : kpDisplay}
          </div>
          <div className={`text-sm font-semibold ${isSevereStorm ? 'text-red-500' : isHighStorm ? 'text-orange-500' : 'text-slate-500'}`}>
            {stormLevelDisplay} {stormNameDisplay}
          </div>
          {kpTrendLabel && (
            <div className="mt-1 text-xs text-slate-400">
              {kpTrendLabel}
            </div>
          )}
          <div className="mt-1 text-xs text-slate-500">
            {spaceWeather.kpTime
              ? `Valid: ${new Date(spaceWeather.kpTime).toLocaleTimeString()}`
              : 'Pending...'}
          </div>
        </div>

        <div className="bg-slate-800 rounded-lg p-4">
          <div className="text-slate-400 text-sm">Solar Wind (L1)</div>
          <div
            className={`text-2xl font-bold ${
              spaceWeather.solarWindSpeed != null && spaceWeather.solarWindSpeed > 600 ? 'text-red-400' : 'text-orange-400'
            }`}
          >
            {spaceWeather.loading ? '...' : spaceWeather.solarWindSpeed != null ? Math.round(spaceWeather.solarWindSpeed) : '—'}
          </div>
          <div className="text-slate-500 text-sm">km/s (DSCOVR)</div>
          {bzTrendLabel && (
            <div className="mt-1 text-xs text-slate-400">
              {bzTrendLabel}
            </div>
          )}
        </div>

        <div className={`bg-slate-800 rounded-lg p-4 ${njRiskScore != null && njRiskScore >= 70 ? 'border-2 border-orange-500' : ''}`}>
          <div className="text-slate-400 text-sm">NJ GIC Risk</div>
          <div className={`text-2xl font-bold ${njRisk.color}`}>
            {njRiskScore != null ? njRiskScore : '—'}
          </div>
          <div className={`${njRisk.color} text-sm`}>{njRisk.label}</div>
          <div className="mt-1 text-xs text-slate-400">Heuristic (40.8°N)</div>
        </div>

        <div className="bg-slate-800 rounded-lg p-4">
          <div className="text-slate-400 text-sm">Bz Field (L1)</div>
          <div
            className={`text-2xl font-bold ${
              spaceWeather.bz != null && spaceWeather.bz < -5 ? 'text-red-400' : spaceWeather.bz != null && spaceWeather.bz < 0 ? 'text-orange-400' : 'text-green-400'
            }`}
          >
            {spaceWeather.loading ? '...' : bzDisplay}
          </div>
          <div className="text-slate-500 text-sm">
            {spaceWeather.bz != null && spaceWeather.bz < 0 ? 'South (Risk)' : spaceWeather.bz != null ? 'North (Safe)' : 'Unknown'}
          </div>
          <div className="mt-1 text-xs text-slate-400">ρ: {densityDisplay}</div>
        </div>
      </div>

      {/* Data Caveats - Critical for understanding limitations */}
      <div className="mb-6 bg-slate-800 rounded-lg p-4 text-xs text-slate-400 space-y-1">
        <div className="font-semibold text-slate-300 mb-2">⚠ Data Limitations & Caveats</div>
        <div>• <strong>Kp Index:</strong> 3-hour average updated every 3 hours—not real-time storm intensity.</div>
        <div>• <strong>L1 Delay:</strong> Solar wind measurements taken ~1.5M km away; 15-60 min propagation to Earth.</div>
        <div>• <strong>Local Variation:</strong> Actual GIC at your location may differ significantly from model estimates.</div>
        <div>• <strong>Historical Context:</strong> 1989 Salem transformer failure shown for reference, not prediction.</div>
        <div>• <strong>Polling:</strong> Fast data (SW/Bz) every 60s, slow data (Kp/alerts) every 10min—not continuous.</div>
      </div>

      {/* NJ Infrastructure Alert */}
      {isStormActive && (
        <div
          className={`mb-6 ${
            isSevereStorm ? 'bg-red-900/30 border-red-600' : 'bg-orange-900/30 border-orange-600'
          } border rounded-lg p-4`}
        >
          <div className="flex items-start gap-3">
            <div className="text-xl">🏭</div>
            <div className="flex-1">
              <div className={`${isSevereStorm ? 'text-red-200' : 'text-orange-200'} font-semibold mb-1`}>
                Northeast NJ Infrastructure Alert - Live Conditions
              </div>
              <div className={`${isSevereStorm ? 'text-red-300' : 'text-orange-300'} text-sm`}>
                Latitude 40.8°N in active geomagnetic zone. Current Kp {kpDisplay} indicates {stormNameDisplay.toLowerCase()} conditions.
                NJ GIC risk index: {njRiskScore != null ? `${njRiskScore}/100 (${njRisk.label})` : 'calculating...'}.
                {spaceWeather.bz != null && spaceWeather.bz < -10 && ' Strongly southward Bz significantly increases transformer stress.'}
              </div>
              <div className={`${isSevereStorm ? 'text-red-400' : 'text-orange-400'} text-xs mt-2 flex gap-4 flex-wrap`}>
                <span>• Monitor PSEG outages</span>
                <span>• Test backup power</span>
                <span>• GPS degraded</span>
                <span>• Fast updates: 1min</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Content Tabs */}
      <div className="space-y-6">
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <StormVisualization spaceWeather={spaceWeather} />
            <RiskHeatmap />
            <div className="xl:col-span-2">
              <TimelineView />
            </div>
          </div>
        )}

        {activeTab === 'storm' && (
          <div className="space-y-6">
            <StormVisualization spaceWeather={spaceWeather} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RiskHeatmap />
              <div className="bg-slate-800 rounded-lg p-6">
                <h3 className="text-xl font-semibold text-white mb-4">Real-Time SWPC Data</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-slate-300 block mb-2 flex justify-between">
                      <span>Kp Index (3-hr average)</span>
                      <span className="text-xs text-slate-400">{kpTrendLabel}</span>
                    </label>
                    <div className="w-full bg-slate-700 rounded-full h-4 relative">
                      <div
                        className={`h-4 rounded-full ${
                          isSevereStorm ? 'bg-red-500' : isHighStorm ? 'bg-orange-500' : 'bg-yellow-500'
                        }`}
                        style={{ width: `${Math.min(100, (spaceWeather.kp ?? 0) * 11.11)}%` }}
                      />
                      <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
                        {kpDisplay} / 9.0
                      </div>
                    </div>
                  </div>
                  <div>
                    <label className="text-slate-300 block mb-2">NJ GIC Risk Score (Heuristic)</label>
                    <div className="w-full bg-slate-700 rounded-full h-4 relative">
                      <div
                        className={`h-4 rounded-full ${njRiskScore != null && njRiskScore >= 70 ? 'bg-red-500' : 'bg-orange-500'}`}
                        style={{ width: `${njRiskScore ?? 0}%` }}
                      />
                      <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white">
                        {njRiskScore != null ? `${njRiskScore}/100` : '—'}
                      </div>
                    </div>
                  </div>
                  <div className="pt-3 border-t border-slate-700">
                    <div className="text-sm text-slate-400 space-y-1">
                      <div>Density: <span className="text-slate-200">{densityDisplay}</span></div>
                      <div>Bt: <span className="text-slate-200">{spaceWeather.bt != null ? `${spaceWeather.bt.toFixed(1)} nT` : '—'}</span></div>
                      <div>NOAA G-Scale: <span className="text-slate-200">{spaceWeather.noaaGScale ?? 'G0'} ({spaceWeather.noaaGText ?? 'none'})</span></div>
                      <div>Algorithm: <span className="text-slate-200">Kp(60%) + Bz(20%) + V(10%) + ρ(10%)</span></div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'risk' && (
          <div className="space-y-6">
            <RiskHeatmap />
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="bg-slate-800 rounded-lg p-6">
                <h4 className="text-lg font-semibold text-white mb-3">NJ Infrastructure (Live)</h4>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Power Grid Risk</span>
                    <span className={njRisk.color + ' font-semibold'}>{njRisk.label}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Transformer Stress</span>
                    <span className={`font-semibold ${isSevereStorm ? 'text-red-400' : isHighStorm ? 'text-orange-400' : 'text-yellow-400'}`}>
                      {isSevereStorm ? 'HIGH' : isHighStorm ? 'ELEVATED' : isStormActive ? 'WATCH' : 'NORMAL'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">GPS Systems</span>
                    <span className="text-orange-400 font-semibold">
                      {isStormActive ? 'DEGRADED' : 'NORMAL'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Communications</span>
                    <span className="text-orange-400 font-semibold">
                      {isStormActive ? 'DISRUPTED' : 'NORMAL'}
                    </span>
                  </div>
                </div>
                <div className="mt-4 p-3 bg-red-900/20 rounded border border-red-700 text-xs text-red-300">
                  1989: Salem Plant transformer damaged by GIC
                </div>
              </div>

              <div className="bg-slate-800 rounded-lg p-6">
                <h4 className="text-lg font-semibold text-white mb-3">Current Conditions</h4>
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-400">Storm Level</span>
                      <span className="text-red-400 font-semibold">{stormLevelDisplay} {stormNameDisplay}</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2">
                      <div className="bg-red-500 h-2 rounded-full" style={{ width: `${Math.min(100, ((spaceWeather.kp ?? 0) / 9) * 100)}%` }} />
                    </div>
                  </div>
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-400">GIC Activity</span>
                      <span className={njRisk.color + ' font-semibold'}>{njRisk.label}</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2">
                      <div className="bg-orange-500 h-2 rounded-full" style={{ width: `${njRiskScore ?? 0}%` }} />
                    </div>
                  </div>
                  <div className="mt-4 text-xs text-slate-400">
                    Polling: Fast (SW/Bz) 60s • Slow (Kp) 10min
                  </div>
                </div>
              </div>

              <div className="bg-slate-800 rounded-lg p-6">
                <h4 className="text-lg font-semibold text-white mb-3">Mitigation Actions</h4>
                <ul className="text-slate-300 space-y-2 text-sm">
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">✓</span>
                    <span>Monitor PSEG outage map</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-green-400 mt-1">✓</span>
                    <span>Test backup systems</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-yellow-400 mt-1">⚠</span>
                    <span>GPS ±15-30m error</span>
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-orange-400 mt-1">!</span>
                    <span>Document power issues</span>
                  </li>
                </ul>
                <div className="mt-4 pt-3 border-t border-slate-700">
                  <a href="https://www.swpc.noaa.gov/" target="_blank" rel="noreferrer" className="text-xs text-blue-400 hover:text-blue-300">
                    → NOAA Alerts
                  </a>
                </div>
              </div>
            </div>

            <div className="bg-slate-800 rounded-lg p-6">
              <h4 className="text-lg font-semibold text-white mb-3">NE New Jersey Vulnerability</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h5 className="text-slate-300 font-semibold mb-2 text-sm">Geologic Factors</h5>
                  <ul className="text-slate-400 text-sm space-y-1">
                    <li>• Piedmont formation → high resistivity</li>
                    <li>• 40.8°N → moderate GMD zone</li>
                    <li>• Complex tectonics → field amplification</li>
                  </ul>
                </div>
                <div>
                  <h5 className="text-slate-300 font-semibold mb-2 text-sm">Grid Infrastructure</h5>
                  <ul className="text-slate-400 text-sm space-y-1">
                    <li>• 70%+ equipment &gt;25 years old</li>
                    <li>• HV transformers = single points of failure</li>
                    <li>• 12-24 month replacement lead time</li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'timeline' && <TimelineView />}
        {activeTab === 'network' && <NetworkGraph />}
      </div>

      {/* Footer */}
      <div className="mt-8 pt-6 border-t border-slate-700">
        <div className="text-slate-500 text-sm text-center space-y-2">
          <div>
            Geomagnetic Resilience Dashboard v2.2 • NE New Jersey •
            Last: {spaceWeather.lastUpdated?.toLocaleString() ?? 'Loading...'}
          </div>
          <div className="text-xs">
            Live: NOAA SWPC (fast: 1min, slow: 10min) • USGS Maps • DOE OE-417 • PLOS One 2025
          </div>
          {spaceWeather.kp != null && (
            <div
              className={`text-xs ${
                isSevereStorm ? 'text-red-400' : isHighStorm ? 'text-orange-400' : isStormActive ? 'text-yellow-400' : 'text-green-400'
              }`}
            >
              {stormLevelDisplay} {stormNameDisplay} • Kp {kpDisplay} •
              {spaceWeather.solarWindSpeed != null && ` SW ${Math.round(spaceWeather.solarWindSpeed)} km/s`} •
              NJ GIC {njRiskScore != null ? `${njRiskScore}/100` : '—'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MainDashboard;
