# Authors: Alexander John Balagso, Marc Aaron Africano

"""Statistics and analytics module for crash data.

Provides detailed statistics, injury breakdowns, contributing factors,
vehicle type analysis, and search capabilities.
"""

from typing import Any, Dict, List
from datetime import datetime


def get_detailed_stats(data: Any) -> Dict[str, Any]:
    """Get comprehensive statistics from crash data.
    
    Returns detailed metrics including injuries by type, vehicle information,
    contributing factors, and borough distribution.
    """
    stats = {}
    
    if hasattr(data, "shape"):
        # pandas DataFrame
        import pandas as pd
        df = data
        
        # Basic counts
        stats["total_accidents"] = int(df.shape[0])
        stats["total_records"] = int(df.shape[0])
        stats["total_columns"] = int(df.shape[1])
        
        # Injury/Death breakdown
        stats["total_injured"] = int(pd.to_numeric(df.get("number_of_persons_injured", 0), errors="coerce").fillna(0).sum())
        stats["total_killed"] = int(pd.to_numeric(df.get("number_of_persons_killed", 0), errors="coerce").fillna(0).sum())
        stats["pedestrians_injured"] = int(pd.to_numeric(df.get("number_of_pedestrians_injured", 0), errors="coerce").fillna(0).sum())
        stats["pedestrians_killed"] = int(pd.to_numeric(df.get("number_of_pedestrians_killed", 0), errors="coerce").fillna(0).sum())
        stats["cyclists_injured"] = int(pd.to_numeric(df.get("number_of_cyclist_injured", 0), errors="coerce").fillna(0).sum())
        stats["cyclists_killed"] = int(pd.to_numeric(df.get("number_of_cyclist_killed", 0), errors="coerce").fillna(0).sum())
        stats["motorists_injured"] = int(pd.to_numeric(df.get("number_of_motorist_injured", 0), errors="coerce").fillna(0).sum())
        stats["motorists_killed"] = int(pd.to_numeric(df.get("number_of_motorist_killed", 0), errors="coerce").fillna(0).sum())
        
        # Top streets
        if "on_street_name" in df.columns:
            stats["top_streets"] = df["on_street_name"].value_counts(dropna=True).head(10).to_dict()
        
        # Boroughs
        if "borough" in df.columns:
            stats["accidents_by_borough"] = df["borough"].value_counts(dropna=True).to_dict()
        
        # Contributing factors
        if "contributing_factor_vehicle_1" in df.columns:
            stats["top_contributing_factors"] = (
                df["contributing_factor_vehicle_1"].value_counts(dropna=True).head(10).to_dict()
            )
        
        # Vehicle types
        vehicle_counts = {}
        for col in ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"]:
            if col in df.columns:
                vc = df[col].value_counts(dropna=True)
                for vtype, count in vc.items():
                    vehicle_counts[vtype] = vehicle_counts.get(vtype, 0) + count
        stats["vehicle_types"] = dict(sorted(vehicle_counts.items(), key=lambda x: x[1], reverse=True)[:20])
        
        # Missing data report
        stats["missing_data"] = {}
        for col in df.columns:
            missing = int(df[col].isna().sum())
            if missing > 0:
                stats["missing_data"][col] = missing
        
    else:
        # list of dicts
        rows = data if isinstance(data, list) else []
        
        stats["total_accidents"] = len(rows)
        stats["total_records"] = len(rows)
        stats["total_columns"] = len(rows[0].keys()) if rows else 0
        
        # Injury breakdown
        inj, killed = 0, 0
        ped_inj, ped_kill = 0, 0
        cyc_inj, cyc_kill = 0, 0
        mot_inj, mot_kill = 0, 0
        street_counts, borough_counts, factor_counts, vehicle_counts = {}, {}, {}, {}
        missing_data = {}
        
        for r in rows:
            try:
                inj += int(r.get("number_of_persons_injured") or 0)
            except:
                pass
            try:
                killed += int(r.get("number_of_persons_killed") or 0)
            except:
                pass
            try:
                ped_inj += int(r.get("number_of_pedestrians_injured") or 0)
            except:
                pass
            try:
                ped_kill += int(r.get("number_of_pedestrians_killed") or 0)
            except:
                pass
            try:
                cyc_inj += int(r.get("number_of_cyclist_injured") or 0)
            except:
                pass
            try:
                cyc_kill += int(r.get("number_of_cyclist_killed") or 0)
            except:
                pass
            try:
                mot_inj += int(r.get("number_of_motorist_injured") or 0)
            except:
                pass
            try:
                mot_kill += int(r.get("number_of_motorist_killed") or 0)
            except:
                pass
            
            # Streets
            street = r.get("on_street_name", "").strip()
            if street:
                street_counts[street] = street_counts.get(street, 0) + 1
            
            # Boroughs
            borough = r.get("borough", "").strip()
            if borough:
                borough_counts[borough] = borough_counts.get(borough, 0) + 1
            
            # Contributing factors
            factor = r.get("contributing_factor_vehicle_1", "").strip()
            if factor:
                factor_counts[factor] = factor_counts.get(factor, 0) + 1
            
            # Vehicle types
            for col in ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"]:
                vtype = r.get(col, "").strip()
                if vtype:
                    vehicle_counts[vtype] = vehicle_counts.get(vtype, 0) + 1
        
        stats["total_injured"] = inj
        stats["total_killed"] = killed
        stats["pedestrians_injured"] = ped_inj
        stats["pedestrians_killed"] = ped_kill
        stats["cyclists_injured"] = cyc_inj
        stats["cyclists_killed"] = cyc_kill
        stats["motorists_injured"] = mot_inj
        stats["motorists_killed"] = mot_kill
        stats["top_streets"] = dict(sorted(street_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        stats["accidents_by_borough"] = dict(sorted(borough_counts.items(), key=lambda x: x[1], reverse=True))
        stats["top_contributing_factors"] = dict(sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        stats["vehicle_types"] = dict(sorted(vehicle_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    
    return stats


def search_by_vehicle_type(data: Any, vehicle_type: str) -> List[Dict]:
    """Search crashes by vehicle type.
    
    Searches all vehicle type columns (vehicle_type_code1-5) for matches.
    Returns matching crash records.
    """
    results = []
    vtype_lower = vehicle_type.lower().strip()
    
    if hasattr(data, "to_dict"):
        # pandas DataFrame
        rows = data.to_dict(orient="records")
    else:
        rows = data if isinstance(data, list) else []
    
    for row in rows:
        for col in ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"]:
            vtype = str(row.get(col, "")).lower().strip()
            if vtype_lower in vtype:
                results.append(row)
                break  # Only add each row once
    
    return results


def filter_by_contributing_factor(data: Any, factor: str) -> List[Dict]:
    """Filter crashes by contributing factor.
    
    Searches contributing_factor_vehicle columns for matches.
    """
    results = []
    factor_lower = factor.lower().strip()
    
    if hasattr(data, "to_dict"):
        rows = data.to_dict(orient="records")
    else:
        rows = data if isinstance(data, list) else []
    
    for row in rows:
        for col in ["contributing_factor_vehicle_1", "contributing_factor_vehicle_2", 
                    "contributing_factor_vehicle_3", "contributing_factor_vehicle_4", "contributing_factor_vehicle_5"]:
            factor_val = str(row.get(col, "")).lower().strip()
            if factor_lower in factor_val:
                results.append(row)
                break
    
    return results


def filter_by_borough(data: Any, borough: str) -> List[Dict]:
    """Filter crashes by borough."""
    results = []
    borough_lower = borough.lower().strip()
    
    if hasattr(data, "to_dict"):
        rows = data.to_dict(orient="records")
    else:
        rows = data if isinstance(data, list) else []
    
    for row in rows:
        b = str(row.get("borough", "")).lower().strip()
        if borough_lower in b or borough_lower == b:
            results.append(row)
    
    return results


def get_vehicle_types_list(data: Any) -> List[str]:
    """Get list of unique vehicle types in the dataset."""
    vehicles = set()
    
    # Convert to list of dicts if it's a pandas DataFrame
    if hasattr(data, "to_dict"):
        try:
            rows = data.to_dict(orient="records")
        except:
            rows = []
    elif isinstance(data, list):
        rows = data
    else:
        return []
    
    # Extract vehicle types from all rows
    for row in rows:
        for col in ["vehicle_type_code1", "vehicle_type_code2", "vehicle_type_code3", "vehicle_type_code4", "vehicle_type_code5"]:
            vtype = str(row.get(col, "")).strip()
            if vtype and vtype.lower() != "nan":
                vehicles.add(vtype)
    
    return sorted([v for v in vehicles if v])


def get_boroughs_list(data: Any) -> List[str]:
    """Get list of unique boroughs in the dataset."""
    boroughs = set()
    
    # Convert to list of dicts if it's a pandas DataFrame
    if hasattr(data, "to_dict"):
        try:
            rows = data.to_dict(orient="records")
        except:
            rows = []
    elif isinstance(data, list):
        rows = data
    else:
        return []
    
    # Extract boroughs from all rows
    for row in rows:
        borough = str(row.get("borough", "")).strip()
        if borough and borough.lower() != "nan":
            boroughs.add(borough)
    
    return sorted([b for b in boroughs if b])


def print_stats_dashboard(stats: Dict) -> None:
    """Print a formatted statistics dashboard."""
    print("\n" + "="*70)
    print("ACCIDENT STATISTICS DASHBOARD")
    print("="*70)
    
    print("\n📊 OVERVIEW")
    print(f"  Total Accidents: {stats.get('total_accidents', 0)}")
    print(f"  Total Records: {stats.get('total_records', 0)}")
    
    print("\n🚗 INJURY STATISTICS")
    print(f"  Total Injured: {stats.get('total_injured', 0)}")
    print(f"  Total Killed: {stats.get('total_killed', 0)}")
    print(f"    ├─ Pedestrians Injured: {stats.get('pedestrians_injured', 0)}")
    print(f"    ├─ Pedestrians Killed: {stats.get('pedestrians_killed', 0)}")
    print(f"    ├─ Cyclists Injured: {stats.get('cyclists_injured', 0)}")
    print(f"    ├─ Cyclists Killed: {stats.get('cyclists_killed', 0)}")
    print(f"    ├─ Motorists Injured: {stats.get('motorists_injured', 0)}")
    print(f"    └─ Motorists Killed: {stats.get('motorists_killed', 0)}")
    
    if stats.get("accidents_by_borough"):
        print("\n🗺️  ACCIDENTS BY BOROUGH")
        for borough, count in stats["accidents_by_borough"].items():
            print(f"  {borough}: {count}")
    
    if stats.get("top_streets"):
        print("\n📍 TOP 10 STREETS")
        for i, (street, count) in enumerate(list(stats["top_streets"].items())[:10], 1):
            print(f"  {i:2d}. {street}: {count}")
    
    if stats.get("top_contributing_factors"):
        print("\n⚠️  TOP CONTRIBUTING FACTORS")
        for i, (factor, count) in enumerate(list(stats["top_contributing_factors"].items())[:10], 1):
            print(f"  {i:2d}. {factor}: {count}")
    
    if stats.get("vehicle_types"):
        print("\n🚙 VEHICLE TYPES INVOLVED")
        for i, (vtype, count) in enumerate(list(stats["vehicle_types"].items())[:15], 1):
            print(f"  {i:2d}. {vtype}: {count}")
    
    print("\n" + "="*70 + "\n")


__all__ = [
    "get_detailed_stats",
    "search_by_vehicle_type",
    "filter_by_contributing_factor",
    "filter_by_borough",
    "get_vehicle_types_list",
    "get_boroughs_list",
    "print_stats_dashboard",
]
