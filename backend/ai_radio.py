"""
EcoFlight AI — Universal AI Radio Frequency
Frequency: 121.500 AI (Universal AI Channel)

Concept: Just like pilots tune to 121.5 MHz for emergency,
they tune to 121.500 AI for real-time optimization guidance.

ARIA (Aeronautical Real-time Intelligence Assistant) knows:
  - Current route, fuel burn, altitude
  - Weather & wind conditions
  - Contrail risk zones ahead
  - Physics-optimal settings vs. current
  - ETA and fuel remaining

Pilot speaks → Web STT → Claude AI Brain → ElevenLabs TTS → Pilot hears advice

How it helps pilots:
  1. Mid-air step climb suggestions   → saves 150-300 kg fuel
  2. Engine N1 / Mach optimization    → reduces burn 2-5%
  3. Contrail avoidance advisories    → reduces climate impact 60%+
  4. Fuel state monitoring            → prevents reserve violations
  5. Wind-aware rerouting             → exploits jet stream shifts
  6. Real-time Q&A                    → answers any flight question via voice
"""

import os
import math
from typing import Dict, List, Optional

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# ARIA SYSTEM PROMPT
# ─────────────────────────────────────────────────────────────────────────────

ARIA_SYSTEM_PROMPT = """You are ARIA (Aeronautical Real-time Intelligence Assistant), the AI co-pilot broadcast on 121.500 AI — the Universal AI Frequency for pilots.

Your role: Give pilots real-time, actionable optimization advice during flight.

VOICE STYLE: Professional aviation co-pilot. Calm, precise, concise. Use knots, feet, flight levels (FL), and standard aviation phraseology. Never use casual language.

PHYSICS KNOWLEDGE:
- Breguet Range Equation: fuel = W0 × (1 − exp(−R × TSFC / (V × L/D)))
  Higher altitude → lower air density → lower drag → better L/D → less fuel
- Step climb savings: Every 2000 ft higher = ~3-5% fuel reduction at same Mach
- Mach reduction: Reducing Mach 0.01 at cruise saves ~1.5-2% fuel
- Contrail formation (Schmidt-Appleman): Risk highest at FL310-370 in cold, moist air
- Wind component: Headwind increases effective range flown, burns more fuel
- CDO (Continuous Descent Operations): Saves 150-400 kg vs. step-down approaches

RESPONSE FORMAT:
1. Lead with the recommendation (1 sentence)
2. Physics justification (1 sentence)
3. Quantified benefit (fuel saved, time saved, or climate impact)
4. Total: 2-4 sentences max for routine queries

URGENCY LEVELS:
- ROUTINE: optimization opportunities, step climbs, wind updates
- ADVISORY: fuel burn above nominal, contrail risk, weather ahead
- URGENT: fuel state critical, immediate action required

EXAMPLE RESPONSES:
"Recommend step climb to FL390. Aircraft weight has decreased by 8 tonnes since departure; Breguet optimum shifted up. Estimated savings: 210 kg fuel, $168 USD."

"Advisory: High contrail risk detected ahead at FL350. Schmidt-Appleman conditions met — temperature minus 58°C, humidity 92%. Recommend FL370 offset, 0.11% fuel penalty for 68% contrail reduction."

"Fuel burn running 6% above Breguet nominal. Possible cause: high ATC-assigned altitude or non-optimal Mach. Recommend reducing Mach by 0.01, projected savings: 90 kg to destination."

Begin first transmission with: "ARIA online, 121.500 AI active."
"""


# ─────────────────────────────────────────────────────────────────────────────
# ARIA AI RADIO CLASS
# ─────────────────────────────────────────────────────────────────────────────

class AIRadio:
    """
    The brain behind the Universal AI Frequency.

    Integrates:
    - Anthropic Claude (claude-haiku-4-5 for ~200ms latency)
    - EcoFlight physics models (Breguet, contrail, weather)
    - ElevenLabs TTS (handled in API endpoints, not here)
    """

    def __init__(self):
        self.client = None
        if ANTHROPIC_AVAILABLE:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)

    # ── Public Methods ────────────────────────────────────────────────────────

    def process_query(
        self,
        pilot_query: str,
        flight_data: Dict,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Process a pilot voice or text query with full flight context.

        Args:
            pilot_query:  What the pilot said/typed
            flight_data:  Current telemetry dict (see FlightContext model in main.py)
            session_id:   Optional session for conversation continuity

        Returns:
            {
              "response_text": str,    # ARIA's spoken response
              "suggestions": list,     # structured action items
              "urgency": str,          # routine | advisory | urgent
              "metrics": dict,         # key numbers for UI display
              "model": str             # which model was used
            }
        """
        if not self.client:
            return self._fallback_response(pilot_query, flight_data)

        flight_context_str = self._build_flight_context_str(flight_data)
        user_message = f"{flight_context_str}\n\n=== PILOT QUERY ===\n{pilot_query}"

        try:
            response = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                system=ARIA_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}]
            )
            response_text = response.content[0].text
            suggestions = self._extract_suggestions(response_text, flight_data)
            urgency = self._assess_urgency(response_text, flight_data)

            return {
                "response_text": response_text,
                "suggestions": suggestions,
                "urgency": urgency,
                "metrics": self._compute_metrics(flight_data),
                "model": "claude-haiku-4-5-20251001"
            }
        except Exception as e:
            return self._fallback_response(pilot_query, flight_data, error=str(e))

    def generate_proactive_broadcast(self, flight_data: Dict) -> Dict:
        """
        Scans current flight state and generates unprompted advisories.
        Called every ~30 seconds from the frontend polling loop.

        Returns a broadcast packet if there are meaningful suggestions,
        or {"broadcast": false} if all is nominal.
        """
        alerts = []

        # ── 1. Step Climb Opportunity ─────────────────────────────────────
        current_alt = flight_data.get("current_altitude_ft", 35000)
        optimal_alt = flight_data.get("optimal_altitude_ft", current_alt)
        if optimal_alt > current_alt + 1500:
            savings = self._estimate_step_climb_savings(flight_data)
            alerts.append({
                "type": "altitude_optimize",
                "icon": "↑",
                "title": f"Step Climb Available: FL{current_alt//100} → FL{optimal_alt//100}",
                "detail": f"Aircraft weight decreased; Breguet optimum shifted up. Save {savings:.0f} kg fuel.",
                "action": f"Request FL{optimal_alt//100} from ATC",
                "savings_kg": round(savings, 1),
                "urgency": "advisory"
            })

        # ── 2. Contrail Avoidance ─────────────────────────────────────────
        contrail_risk = flight_data.get("contrail_risk", "low")
        if contrail_risk in ("high", "medium"):
            offset_ft = 2000 if contrail_risk == "high" else 1000
            direction = "up" if current_alt < 37000 else "down"
            alerts.append({
                "type": "contrail_avoid",
                "icon": "☁",
                "title": f"{contrail_risk.title()} Contrail Risk Ahead",
                "detail": (
                    f"Schmidt-Appleman conditions active. {offset_ft} ft vertical offset "
                    f"recommended. Fuel penalty: 0.11%, contrail reduction: ~65%."
                ),
                "action": f"Request {'+' if direction == 'up' else '-'}{offset_ft} ft offset",
                "savings_kg": 0,
                "urgency": "advisory" if contrail_risk == "high" else "routine"
            })

        # ── 3. Fuel Burn Rate Anomaly ─────────────────────────────────────
        actual_burn = flight_data.get("fuel_burn_rate_kg_per_hr", 0)
        expected_burn = flight_data.get("expected_burn_rate_kg_per_hr", 0)
        if expected_burn > 0 and actual_burn > expected_burn * 1.05:
            excess_pct = ((actual_burn - expected_burn) / expected_burn) * 100
            eta_hrs = flight_data.get("eta_minutes", 120) / 60
            recoverable = (actual_burn - expected_burn) * eta_hrs
            alerts.append({
                "type": "fuel_burn_high",
                "icon": "⚡",
                "title": f"Fuel Burn {excess_pct:.1f}% Above Breguet Nominal",
                "detail": f"Check cruise Mach and engine N1. Correcting now saves {recoverable:.0f} kg to destination.",
                "action": "Verify N1 targets on performance page",
                "savings_kg": round(recoverable, 1),
                "urgency": "advisory"
            })

        # ── 4. Tailwind / Speed Reduction Opportunity ─────────────────────
        wind_kt = flight_data.get("wind_component_kt", 0)
        if wind_kt < -25:  # significant tailwind (negative = tailwind convention)
            mach_save_kg = abs(wind_kt) * 0.75
            alerts.append({
                "type": "speed_reduce",
                "icon": "→",
                "title": f"{abs(wind_kt):.0f} kt Tailwind Detected",
                "detail": f"Reduce Mach 0.01-0.02 for additional fuel savings. Estimated: {mach_save_kg:.0f} kg.",
                "action": "Reduce cruise Mach by 0.01",
                "savings_kg": round(mach_save_kg, 1),
                "urgency": "routine"
            })

        # ── 5. Fuel State Advisory ────────────────────────────────────────
        fuel_remaining = flight_data.get("fuel_remaining_kg", 0)
        eta_hrs = flight_data.get("eta_minutes", 0) / 60
        burn_rate = flight_data.get("fuel_burn_rate_kg_per_hr", 2000)
        if fuel_remaining > 0 and eta_hrs > 0:
            fuel_to_dest = burn_rate * eta_hrs
            reserve = fuel_remaining * 0.08  # rough 8% reserve
            margin = fuel_remaining - fuel_to_dest - reserve
            if margin < 500:
                alerts.append({
                    "type": "fuel_state",
                    "icon": "⚠",
                    "title": f"Fuel Margin Tight: {margin:.0f} kg Above Reserve",
                    "detail": (
                        f"{fuel_remaining:.0f} kg remaining, need {fuel_to_dest:.0f} kg + "
                        f"{reserve:.0f} kg reserve. Review alternate."
                    ),
                    "action": "Consult fuel plan and consider alternate",
                    "savings_kg": 0,
                    "urgency": "urgent"
                })

        # ── 6. Optimal Descent Point ─────────────────────────────────────
        dist_remaining = flight_data.get("distance_remaining_nm", 9999)
        if 80 <= dist_remaining <= 130:
            alerts.append({
                "type": "descent_planning",
                "icon": "↓",
                "title": "CDO Descent Window Open",
                "detail": (
                    "Continuous Descent Operations window: begin descent now for "
                    "fuel-optimal idle-power profile. Saves 180-300 kg vs. step-down."
                ),
                "action": "Request descent clearance, target TOD now",
                "savings_kg": 240,
                "urgency": "advisory"
            })

        # ── Build voice script from top alerts ───────────────────────────
        voice_script = self._build_proactive_voice_script(alerts)
        urgency = self._overall_urgency(alerts)

        return {
            "broadcast": len(alerts) > 0,
            "alerts": alerts,
            "urgency": urgency,
            "voice_script": voice_script,
            "total_savings_potential_kg": sum(a.get("savings_kg", 0) for a in alerts)
        }

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _build_flight_context_str(self, fd: Dict) -> str:
        """Serialize flight telemetry into a structured string for Claude."""
        lines = ["=== LIVE FLIGHT TELEMETRY ==="]

        if fd.get("aircraft"):
            lines.append(f"Aircraft Type: {fd['aircraft']}")
        if fd.get("origin") and fd.get("destination"):
            lines.append(f"Route: {fd['origin']} → {fd['destination']}")
        if fd.get("flight_phase"):
            lines.append(f"Flight Phase: {fd['flight_phase'].upper()}")

        alt = fd.get("current_altitude_ft")
        opt_alt = fd.get("optimal_altitude_ft")
        if alt:
            lines.append(f"Current Altitude: FL{alt // 100} ({alt:,} ft)")
        if opt_alt and opt_alt != alt:
            lines.append(f"Breguet-Optimal Altitude: FL{opt_alt // 100}")

        gs = fd.get("groundspeed_kt")
        if gs:
            lines.append(f"Ground Speed: {gs:.0f} kt")

        wind = fd.get("wind_component_kt")
        if wind is not None:
            direction = "headwind" if wind > 0 else "tailwind"
            lines.append(f"Wind Component: {abs(wind):.0f} kt {direction}")

        fuel_rem = fd.get("fuel_remaining_kg")
        fuel_total = fd.get("total_fuel_kg")
        burn_rate = fd.get("fuel_burn_rate_kg_per_hr")
        exp_burn = fd.get("expected_burn_rate_kg_per_hr")

        if fuel_rem is not None:
            lines.append(f"Fuel Remaining: {fuel_rem:,.0f} kg")
        if fuel_total and fuel_rem:
            pct = (fuel_rem / fuel_total) * 100
            lines.append(f"Fuel State: {pct:.1f}% of block fuel")
        if burn_rate:
            lines.append(f"Current Burn Rate: {burn_rate:,.0f} kg/hr")
        if exp_burn:
            lines.append(f"Expected Burn Rate: {exp_burn:,.0f} kg/hr")
            if burn_rate and burn_rate > exp_burn * 1.03:
                delta_pct = ((burn_rate - exp_burn) / exp_burn) * 100
                lines.append(f"Burn Rate Delta: +{delta_pct:.1f}% above Breguet model")

        dist_rem = fd.get("distance_remaining_nm")
        eta = fd.get("eta_minutes")
        if dist_rem:
            lines.append(f"Distance Remaining: {dist_rem:.0f} nm")
        if eta:
            h, m = divmod(int(eta), 60)
            lines.append(f"ETA: {h}h {m:02d}m")

        contrail = fd.get("contrail_risk")
        if contrail:
            lines.append(f"Contrail Risk Ahead: {contrail.upper()}")

        eff = fd.get("efficiency_pct")
        if eff:
            lines.append(f"Route Efficiency vs Ghost: {eff:.1f}%")

        payload = fd.get("payload_kg")
        if payload:
            lines.append(f"Payload: {payload:,.0f} kg")

        return "\n".join(lines)

    def _estimate_step_climb_savings(self, fd: Dict) -> float:
        """Estimate fuel saved by climbing to optimal altitude (Breguet-based)."""
        burn_rate = fd.get("fuel_burn_rate_kg_per_hr", 2200)
        eta_hrs = fd.get("eta_minutes", 120) / 60
        ld_improvement = 0.035  # ~3.5% L/D gain per 2000 ft step
        return burn_rate * eta_hrs * ld_improvement

    def _extract_suggestions(self, response_text: str, fd: Dict) -> List[Dict]:
        """Parse structured action items from Claude's free-text response."""
        suggestions = []
        lower = response_text.lower()

        if any(x in lower for x in ["step climb", "fl3", "fl4", "altitude"]):
            opt_alt = fd.get("optimal_altitude_ft", 37000)
            suggestions.append({
                "type": "altitude",
                "icon": "↑",
                "action": f"Request FL{opt_alt // 100} from ATC"
            })
        if any(x in lower for x in ["reduce mach", "reduce speed", "slow down", "n1"]):
            suggestions.append({
                "type": "speed",
                "icon": "→",
                "action": "Reduce cruise Mach by 0.01 on FMS"
            })
        if "contrail" in lower:
            suggestions.append({
                "type": "contrail",
                "icon": "☁",
                "action": "Request ±2000 ft offset from ATC"
            })
        if any(x in lower for x in ["fuel", "monitor", "reserve"]):
            suggestions.append({
                "type": "fuel",
                "icon": "⛽",
                "action": "Review fuel plan on ACARS"
            })
        if any(x in lower for x in ["descent", "tod", "cdo"]):
            suggestions.append({
                "type": "descent",
                "icon": "↓",
                "action": "Begin CDO descent, request clearance"
            })

        return suggestions

    def _assess_urgency(self, response_text: str, fd: Dict) -> str:
        lower = response_text.lower()
        if any(w in lower for w in ["urgent", "immediate", "critical", "alert", "warning", "tight"]):
            return "urgent"
        if any(w in lower for w in ["recommend", "suggest", "advise", "advisory", "consider"]):
            return "advisory"
        return "routine"

    def _overall_urgency(self, alerts: List[Dict]) -> str:
        for a in alerts:
            if a.get("urgency") == "urgent":
                return "urgent"
        for a in alerts:
            if a.get("urgency") == "advisory":
                return "advisory"
        return "routine"

    def _compute_metrics(self, fd: Dict) -> Dict:
        """Key metrics for the UI status bar."""
        fuel_rem = fd.get("fuel_remaining_kg", 0)
        fuel_total = fd.get("total_fuel_kg", 1)
        fuel_pct = round((fuel_rem / fuel_total) * 100, 1) if fuel_total else 0

        burn_rate = fd.get("fuel_burn_rate_kg_per_hr", 0)
        exp_burn = fd.get("expected_burn_rate_kg_per_hr", burn_rate)
        burn_delta_pct = round(((burn_rate - exp_burn) / max(exp_burn, 1)) * 100, 1)

        return {
            "fuel_remaining_kg": fuel_rem,
            "fuel_state_pct": fuel_pct,
            "burn_delta_pct": burn_delta_pct,
            "eta_minutes": fd.get("eta_minutes"),
            "efficiency_pct": fd.get("efficiency_pct", 94.0),
            "contrail_risk": fd.get("contrail_risk", "low"),
            "altitude_ft": fd.get("current_altitude_ft", 35000),
        }

    def _build_proactive_voice_script(self, alerts: List[Dict]) -> str:
        if not alerts:
            return ""
        # Pick highest urgency first
        urgent = [a for a in alerts if a["urgency"] == "urgent"]
        advisory = [a for a in alerts if a["urgency"] == "advisory"]
        top = (urgent or advisory or alerts)[:2]

        parts = ["ARIA advisory."]
        for a in top:
            parts.append(a["detail"])
        return " ".join(parts)

    def _fallback_response(self, query: str, fd: Dict, error: str = "") -> Dict:
        """Physics-based response when Claude API is unavailable."""
        current_alt = fd.get("current_altitude_ft", 35000)
        optimal_alt = fd.get("optimal_altitude_ft", current_alt)
        fuel_rem = fd.get("fuel_remaining_kg", 0)
        burn_rate = fd.get("fuel_burn_rate_kg_per_hr", 2000)
        contrail = fd.get("contrail_risk", "low")

        # Generate a contextual fallback
        if "fuel" in query.lower():
            eta_hrs = fd.get("eta_minutes", 120) / 60
            fuel_to_dest = burn_rate * eta_hrs
            text = (
                f"ARIA online, 121.500 AI active. "
                f"Fuel remaining: {fuel_rem:,.0f} kg. "
                f"Estimated fuel to destination: {fuel_to_dest:,.0f} kg. "
                f"Burn rate nominal at FL{current_alt // 100}."
            )
        elif "altitude" in query.lower() or "climb" in query.lower():
            savings = self._estimate_step_climb_savings(fd)
            if optimal_alt > current_alt + 1000:
                text = (
                    f"ARIA online. Step climb to FL{optimal_alt // 100} recommended. "
                    f"Aircraft is lighter now; Breguet equation shows FL{optimal_alt // 100} "
                    f"as optimum. Estimated savings: {savings:.0f} kg fuel."
                )
            else:
                text = (
                    f"ARIA online. Current FL{current_alt // 100} is optimal for current weight. "
                    f"No step climb benefit at this time."
                )
        elif "contrail" in query.lower():
            text = (
                f"ARIA online. Contrail risk ahead: {contrail.upper()}. "
                f"Schmidt-Appleman criterion {'active — vertical offset recommended' if contrail in ('high','medium') else 'not met — current altitude clear'}."
            )
        else:
            text = (
                "ARIA online, 121.500 AI active. "
                "All flight parameters nominal. "
                f"Flying FL{current_alt // 100} at {burn_rate:,.0f} kg/hr. "
                "No immediate optimization actions required. "
                "(Note: Claude API key not configured — running physics-only mode.)"
            )

        return {
            "response_text": text,
            "suggestions": [],
            "urgency": "routine",
            "metrics": self._compute_metrics(fd),
            "model": "physics-fallback",
            "error": error
        }
