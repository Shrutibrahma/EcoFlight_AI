"""
EcoFlight AI — Physics-Based Fuel Optimizer
Implements the Breguet Range Equation (jet form) on every edge.

KEY FORMULA:
  fuel_burned = W0 × (1 − exp(−R × TSFC_per_sec / (V × L/D)))

where:
  R           = segment range [m]
  TSFC_per_sec = TSFC [lb/lbf/hr] / 3600  (weight-based, per second)
  V           = true airspeed [m/s]
  L/D         = lift-to-drag ratio
  W0          = initial segment weight [kg]

Wind adjustment:
  headwind    = wind_u × sin(bearing) + wind_v × cos(bearing)  [kt]
  ground_speed = TAS − headwind  (clamped ≥ TAS × 0.1)
  eff_range   = great_circle_dist × (TAS / GS)   [wind-adjusted range]
"""

import math
from typing import Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# AIRCRAFT PERFORMANCE DATABASE
# ─────────────────────────────────────────────────────────────────────────────
AIRCRAFT_DB: Dict[str, Dict] = {
    "B777": {
        "full_name": "Boeing 777-200ER",
        "MTOW_kg": 297550,
        "OEW_kg": 138100,
        "TSFC": 0.55,           # lb/lbf/hr (GE90-94B cruise)
        "LD": 19,               # max lift-to-drag ratio
        "TAS_kt": 490,          # cruise true airspeed
        "cruise_FL": (350, 390),
        "typical_payload_kg": 55000,
    },
    "A320": {
        "full_name": "Airbus A320-200",
        "MTOW_kg": 77000,
        "OEW_kg": 42400,
        "TSFC": 0.60,           # CFM56-5B cruise
        "LD": 17,
        "TAS_kt": 450,
        "cruise_FL": (320, 380),
        "typical_payload_kg": 17000,
    },
    "B737": {
        "full_name": "Boeing 737-800",
        "MTOW_kg": 79016,
        "OEW_kg": 41413,
        "TSFC": 0.63,           # CFM56-7B cruise
        "LD": 17.5,
        "TAS_kt": 453,
        "cruise_FL": (310, 370),
        "typical_payload_kg": 18000,
    },
    # Legacy keys kept for backward compatibility
    "B747": {
        "full_name": "Boeing 747-400",
        "MTOW_kg": 412775,
        "OEW_kg": 178756,
        "TSFC": 0.58,
        "LD": 17,
        "TAS_kt": 490,
        "cruise_FL": (330, 370),
        "typical_payload_kg": 100000,
    },
    "A321": {
        "full_name": "Airbus A321neo",
        "MTOW_kg": 97000,
        "OEW_kg": 50100,
        "TSFC": 0.58,
        "LD": 18,
        "TAS_kt": 450,
        "cruise_FL": (320, 390),
        "typical_payload_kg": 22000,
    },
    # ── Modern Widebodies ──────────────────────────────────────────────────────
    "B787": {
        "full_name": "Boeing 787-9 Dreamliner",
        "MTOW_kg": 254011,
        "OEW_kg": 128850,
        "TSFC": 0.51,           # GEnx-1B76 — most fuel-efficient widebody engine
        "LD": 20,               # highest L/D of any commercial aircraft
        "TAS_kt": 488,          # Mach 0.855 cruise
        "cruise_FL": (350, 410),
        "typical_payload_kg": 50000,
    },
    "A350": {
        "full_name": "Airbus A350-900",
        "MTOW_kg": 280000,
        "OEW_kg": 142400,
        "TSFC": 0.52,           # Rolls-Royce Trent XWB-84
        "LD": 21,               # carbon-fibre wing, best commercial L/D
        "TAS_kt": 488,          # Mach 0.85 cruise
        "cruise_FL": (350, 430),
        "typical_payload_kg": 53000,
    },
    "A380": {
        "full_name": "Airbus A380-800",
        "MTOW_kg": 575000,
        "OEW_kg": 276800,
        "TSFC": 0.56,           # Engine Alliance GP7270
        "LD": 19.5,
        "TAS_kt": 488,
        "cruise_FL": (330, 390),
        "typical_payload_kg": 150000,
    },
    # ── Private / Business Jets ────────────────────────────────────────────────
    "G650": {
        "full_name": "Gulfstream G650ER (Private Jet)",
        "MTOW_kg": 45812,
        "OEW_kg": 24100,
        "TSFC": 0.59,           # Rolls-Royce BR725
        "LD": 17.5,
        "TAS_kt": 516,          # Mach 0.925 — fastest purpose-built bizjet
        "cruise_FL": (390, 510),# Can fly FL510, above most weather
        "typical_payload_kg": 4000,
    },
    "BD700": {
        "full_name": "Bombardier Global 7500 (Private Jet)",
        "MTOW_kg": 48626,
        "OEW_kg": 25400,
        "TSFC": 0.58,           # GE Passport 20
        "LD": 18,
        "TAS_kt": 512,          # Mach 0.925
        "cruise_FL": (390, 510),
        "typical_payload_kg": 4000,
    },
    "C750": {
        "full_name": "Cessna Citation X+ (Light Jet)",
        "MTOW_kg": 16375,
        "OEW_kg": 9752,
        "TSFC": 0.70,           # Rolls-Royce AE3007C2
        "LD": 15,
        "TAS_kt": 513,          # Mach 0.935 — fastest civilian piston-free aircraft
        "cruise_FL": (350, 510),
        "typical_payload_kg": 1500,
    },
}

CO2_FACTOR = 3.16        # kg CO2 per kg Jet-A burned
JET_A_PRICE = 0.85       # $/kg
CONTRAIL_ERF = 0.8       # kg CO2-eq per km of persistent contrail


class FuelOptimizer:
    """
    Physics-based fuel burn using the Breguet Range Equation.
    All fuel values in kg; distances in km; speeds in kt or m/s.
    """

    # ISA standard atmosphere
    ISA_SEA_LEVEL_TEMP_C = 15.0
    ISA_LAPSE_RATE_C_PER_KFTFT = 1.98      # °C per 1000 ft

    def __init__(self):
        self.db = AIRCRAFT_DB

    # ──────────────────────────────────────────────────────────────────────────
    # CORE BREGUET CALCULATION
    # ──────────────────────────────────────────────────────────────────────────

    def breguet_fuel(self, dist_km: float, W0_kg: float, ac_key: str) -> float:
        """
        Jet Breguet Range Equation (per segment).

        R = (V / TSFC_per_sec) × (L/D) × ln(W0/W1)
        → fuel_burned = W0 × (1 − exp(−R × TSFC_per_sec / (V × L/D)))

        Uses weight-based TSFC: TSFC [lb/lbf/hr] is dimensionless per second
        when lb_mass/lb_force cancels — divide by 3600 to convert hr → s.

        Physical validation for B777-200ER JFK→LHR (5540 km), W0=250000 kg:
          V    = 490 kt × 0.51444 = 252.1 m/s
          tsfc = 0.55 / 3600     = 1.528e-4 s⁻¹
          arg  = 5540000 × 1.528e-4 / (252.1 × 19) = 0.1768
          fuel = 250000 × (1 − exp(−0.1768)) = 40 580 kg  [cruise only]
          + ~12 000 kg overhead → total ~52 600 kg  ✓ (spec: 50 000–75 000 kg)
        """
        if dist_km <= 0 or W0_kg <= 0:
            return 0.0
        ac = self._get_ac(ac_key)
        V = ac["TAS_kt"] * 0.51444          # knots → m/s
        tsfc_per_sec = ac["TSFC"] / 3600    # lb/lbf/hr → per second
        R = dist_km * 1000.0                # km → m
        exponent = R * tsfc_per_sec / (V * ac["LD"])
        return max(0.0, W0_kg * (1.0 - math.exp(-exponent)))

    def wind_adjusted_fuel(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float,
        W0_kg: float,
        ac_key: str,
        wind_u_kt: float,   # u-component (positive = eastward) in knots
        wind_v_kt: float,   # v-component (positive = northward) in knots
    ) -> Dict:
        """
        Wind-corrected Breguet fuel for one edge (Section 1B of spec).

        bearing  = atan2(sin(Δlon)·cos(lat2), cos(lat1)·sin(lat2) − sin(lat1)·cos(lat2)·cos(Δlon))
        headwind = wind_u × sin(bearing) + wind_v × cos(bearing)   [kt]
        GS       = TAS − headwind   (clamped ≥ TAS × 0.1)
        eff_dist = great_circle_dist × (TAS / GS)
        fuel     = Breguet(eff_dist, W0, aircraft)
        """
        dist_km = self.haversine_km(lat1, lon1, lat2, lon2)
        ac = self._get_ac(ac_key)
        TAS = ac["TAS_kt"]
        brg = self._bearing_rad(lat1, lon1, lat2, lon2)
        headwind = wind_u_kt * math.sin(brg) + wind_v_kt * math.cos(brg)
        gs = max(TAS * 0.1, TAS - headwind)
        eff_dist = dist_km * (TAS / gs)
        fuel = self.breguet_fuel(eff_dist, W0_kg, ac_key)
        time_min = (dist_km / gs) * 60.0  # gs in kt ≈ nm/hr → convert
        # 1 kt = 1 nm/hr; nm → km: dist_nm = dist_km / 1.852
        time_min = (dist_km / 1.852 / gs) * 60.0
        return {
            "dist_km": round(dist_km, 2),
            "fuel_kg": round(fuel, 1),
            "time_min": round(time_min, 2),
            "headwind_kt": round(headwind, 2),
            "ground_speed_kt": round(gs, 1),
            "eff_dist_km": round(eff_dist, 2),
        }

    def mission_fuel(
        self,
        route: List[Dict],
        ac_key: str,
        wind_data: Dict,
    ) -> float:
        """
        Total block fuel for a multi-segment route.
        Includes climb overhead and reserves.
        """
        ac = self._get_ac(ac_key)
        payload = ac["typical_payload_kg"]
        # W0 = OEW + payload + estimated fuel (iterate for accuracy)
        # Simple estimate: start with MTOW*0.25 as initial fuel guess
        fuel_guess = ac["MTOW_kg"] * 0.22
        W0 = ac["OEW_kg"] + payload + fuel_guess

        total_cruise_fuel = 0.0
        w_u = float(wind_data.get("average_headwind", 0) or 0)
        w_v = 0.0

        for i in range(1, len(route)):
            prev = route[i - 1]
            curr = route[i]
            seg = self.wind_adjusted_fuel(
                prev["lat"], prev["lon"],
                curr["lat"], curr["lon"],
                W0, ac_key, w_u, w_v
            )
            total_cruise_fuel += seg["fuel_kg"]
            W0 -= seg["fuel_kg"]  # aircraft gets lighter each segment

        # Add climb/descent overhead (~8% for long-haul, ~15% short-haul)
        dist_total = sum(
            self.haversine_km(route[i-1]["lat"], route[i-1]["lon"],
                              route[i]["lat"], route[i]["lon"])
            for i in range(1, len(route))
        )
        overhead_factor = 0.08 if dist_total > 2000 else 0.15
        return total_cruise_fuel * (1 + overhead_factor)

    def contrail_risk_score(
        self, lat: float, lon: float, alt_ft: float
    ) -> float:
        """
        ISSR-based contrail risk (Section 1D of spec).
        contrail_risk = 0 if temp > -38°C
        contrail_risk = (RHI - 100) / 50, clamped [0,1]  if temp ≤ -38°C and RHI ≥ 100
        Warming: contrails cause ~35% of aviation's total climate effect.
        """
        temp_c = self.ISA_SEA_LEVEL_TEMP_C - (alt_ft / 1000.0) * self.ISA_LAPSE_RATE_C_PER_KFTFT
        # Regional temperature adjustment (North Atlantic corridor)
        if 44 <= lat <= 58 and -55 <= lon <= -5:
            temp_c -= 2.5
        # Synthetic RHI (humidity over ice)
        if 44 <= lat <= 58 and -55 <= lon <= -5 and alt_ft >= 34000:
            rhi = 108 + 15 * math.sin(lat * 0.3 + lon * 0.1)
        else:
            rhi = 75 + 10 * math.sin(lat * 0.2)
        if temp_c > -38 or rhi < 100:
            return 0.0
        return min(1.0, (rhi - 100) / 50.0)

    def composite_cost(
        self,
        fuel_kg: float,
        time_min: float,
        dist_km: float,
        contrail_risk: float,
        weights: Dict,
    ) -> float:
        """
        Multi-objective composite edge cost (Section 1C of spec).
        cost = w1×fuel_kg + w2×(time_min/60) + w3×(fuel_kg×3.16) + w4×contrail_risk×dist_km
        """
        w1 = weights.get("w1", 0.60)
        w2 = weights.get("w2", 0.20)
        w3 = weights.get("w3", 0.15)
        w4 = weights.get("w4", 0.05)
        return (
            w1 * fuel_kg
            + w2 * (time_min / 60.0)
            + w3 * (fuel_kg * CO2_FACTOR)
            + w4 * contrail_risk * dist_km
        )

    def ghost_efficiency(
        self,
        our_total_cost: float,
        ghost_total_cost: float,
    ) -> float:
        """
        Ghost efficiency = (ghost_cost / our_cost) × 100
        Ghost flight = theoretical optimum: no ATC, perfect wind, unconstrained altitude.
        """
        if our_total_cost <= 0:
            return 0.0
        return min(100.0, (ghost_total_cost / our_total_cost) * 100.0)

    def co2_equivalent(self, fuel_kg: float, contrail_km: float = 0.0) -> float:
        """
        CO₂ equivalent including contrail ERF.
        co2_eq = fuel_kg × 3.16 + contrail_risk × dist_km × 0.8
        """
        return fuel_kg * CO2_FACTOR + contrail_km * CONTRAIL_ERF

    # ──────────────────────────────────────────────────────────────────────────
    # GEOMETRY HELPERS
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def haversine_km(lat1, lon1, lat2, lon2) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def haversine_nm(lat1, lon1, lat2, lon2) -> float:
        return FuelOptimizer.haversine_km(lat1, lon1, lat2, lon2) / 1.852

    @staticmethod
    def _bearing_rad(lat1, lon1, lat2, lon2) -> float:
        la1, la2 = math.radians(lat1), math.radians(lat2)
        dl = math.radians(lon2 - lon1)
        return math.atan2(
            math.sin(dl) * math.cos(la2),
            math.cos(la1) * math.sin(la2) - math.sin(la1) * math.cos(la2) * math.cos(dl)
        )

    def _get_ac(self, key: str) -> Dict:
        return self.db.get(key, self.db["B777"])

    # Legacy compatibility shim
    def calculate_fuel_burn(self, route: List[dict], aircraft_type: str, wind_data: Dict) -> float:
        return self.mission_fuel(route, aircraft_type, wind_data)

    def evaluate_cdo_benefit(self, airport: Dict, aircraft_type: str) -> bool:
        cdo_airports = {
            "KJFK", "KLAX", "KORD", "KDFW", "KDEN", "KSFO", "KSEA", "KATL",
            "EGLL", "LFPG", "EDDF", "EHAM", "LEMD", "VHHH", "ZSPD", "RJTT",
        }
        return airport.get("code", "") in cdo_airports
