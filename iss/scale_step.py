"""
Scale STEP (ISO 10303-21) files by a given factor.

This script reads all .step files in the source directory, multiplies
all geometric coordinates and dimensional values by the scale factor,
and writes the scaled files to a 'scaled' subdirectory.

Entities scaled:
  - CARTESIAN_POINT: all coordinate values
  - CIRCLE: radius
  - CYLINDRICAL_SURFACE: radius
  - CONICAL_SURFACE: radius (angle preserved)
  - VECTOR: magnitude
  - UNCERTAINTY_MEASURE_WITH_UNIT: tolerance value (LENGTH_MEASURE)
  - LINE: (no change needed — defined by point + vector, both scaled)
"""

import os
import re
import glob
import sys

SCALE_FACTOR = 6.0
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DST_DIR = os.path.join(SRC_DIR, "scaled")


def scale_number(match_str: str, factor: float) -> str:
    """Scale a single numeric string, preserving formatting style."""
    try:
        val = float(match_str) * factor
    except ValueError:
        return match_str

    # Preserve scientific notation if original used it
    if 'E' in match_str.upper():
        return f"{val:.15E}"
    
    # For very small numbers that were written without E notation
    # keep reasonable precision
    original_has_dot = '.' in match_str
    if original_has_dot:
        # Count decimal places in original
        decimal_part = match_str.split('.')[-1]
        decimal_places = len(decimal_part)
        # Use at least the same precision, minimum 6
        precision = max(decimal_places, 6)
        formatted = f"{val:.{precision}f}"
        # Strip trailing zeros but keep at least one decimal place
        formatted = formatted.rstrip('0').rstrip('.')
        if '.' not in formatted:
            formatted += '.0'
        return formatted
    else:
        # Integer-like
        if val == int(val):
            return str(int(val))
        return f"{val:.6f}".rstrip('0').rstrip('.')


def scale_cartesian_point(line: str, factor: float) -> str:
    """Scale CARTESIAN_POINT('name',(x,y,z));"""
    pattern = r"(CARTESIAN_POINT\s*\(\s*'[^']*'\s*,\s*\()([^)]+)(\)\s*\))"
    
    def replace_coords(m):
        prefix = m.group(1)
        coords_str = m.group(2)
        suffix = m.group(3)
        
        coords = coords_str.split(',')
        scaled = [scale_number(c.strip(), factor) for c in coords]
        return prefix + ','.join(scaled) + suffix
    
    return re.sub(pattern, replace_coords, line)


def scale_circle(line: str, factor: float) -> str:
    """Scale CIRCLE('name',#ref,radius);"""
    pattern = r"(CIRCLE\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*)([0-9eE.+\-]+)(\s*\))"
    
    def replace_radius(m):
        return m.group(1) + scale_number(m.group(2), factor) + m.group(3)
    
    return re.sub(pattern, replace_radius, line, flags=re.IGNORECASE)


def scale_cylindrical_surface(line: str, factor: float) -> str:
    """Scale CYLINDRICAL_SURFACE('name',#ref,radius);"""
    pattern = r"(CYLINDRICAL_SURFACE\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*)([0-9eE.+\-]+)(\s*\))"
    
    def replace_radius(m):
        return m.group(1) + scale_number(m.group(2), factor) + m.group(3)
    
    return re.sub(pattern, replace_radius, line, flags=re.IGNORECASE)


def scale_conical_surface(line: str, factor: float) -> str:
    """Scale CONICAL_SURFACE('name',#ref,radius,angle); — only radius, not angle."""
    pattern = r"(CONICAL_SURFACE\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*)([0-9eE.+\-]+)(\s*,\s*[0-9eE.+\-]+\s*\))"
    
    def replace_radius(m):
        return m.group(1) + scale_number(m.group(2), factor) + m.group(3)
    
    return re.sub(pattern, replace_radius, line, flags=re.IGNORECASE)


def scale_vector(line: str, factor: float) -> str:
    """Scale VECTOR('name',#ref,magnitude);"""
    pattern = r"(VECTOR\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*)([0-9eE.+\-]+)(\s*\))"
    
    def replace_mag(m):
        return m.group(1) + scale_number(m.group(2), factor) + m.group(3)
    
    return re.sub(pattern, replace_mag, line, flags=re.IGNORECASE)


def scale_uncertainty(line: str, factor: float) -> str:
    """Scale UNCERTAINTY_MEASURE_WITH_UNIT(LENGTH_MEASURE(val),...);"""
    pattern = r"(LENGTH_MEASURE\s*\(\s*)([0-9eE.+\-]+)(\s*\))"
    
    def replace_val(m):
        return m.group(1) + scale_number(m.group(2), factor) + m.group(3)
    
    return re.sub(pattern, replace_val, line, flags=re.IGNORECASE)


def scale_spherical_surface(line: str, factor: float) -> str:
    """Scale SPHERICAL_SURFACE('name',#ref,radius);"""
    pattern = r"(SPHERICAL_SURFACE\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*)([0-9eE.+\-]+)(\s*\))"
    
    def replace_radius(m):
        return m.group(1) + scale_number(m.group(2), factor) + m.group(3)
    
    return re.sub(pattern, replace_radius, line, flags=re.IGNORECASE)


def scale_toroidal_surface(line: str, factor: float) -> str:
    """Scale TOROIDAL_SURFACE('name',#ref,major_radius,minor_radius);"""
    pattern = r"(TOROIDAL_SURFACE\s*\(\s*'[^']*'\s*,\s*#\d+\s*,\s*)([0-9eE.+\-]+)(\s*,\s*)([0-9eE.+\-]+)(\s*\))"
    
    def replace_radii(m):
        return (m.group(1) + scale_number(m.group(2), factor) +
                m.group(3) + scale_number(m.group(4), factor) + m.group(5))
    
    return re.sub(pattern, replace_radii, line, flags=re.IGNORECASE)


def scale_b_spline_curve(line: str, factor: float) -> str:
    """Scale B_SPLINE_CURVE_WITH_KNOTS control point weights — 
    these don't need scaling as they reference CARTESIAN_POINTs by ID.
    But BOUNDED_CURVE / B_SPLINE entities themselves don't store coordinates inline.
    No action needed here."""
    return line


def process_step_file(src_path: str, dst_path: str, factor: float):
    """Process a single STEP file: scale all geometric entities."""
    with open(src_path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # STEP files can have multi-line entities. We need to join continued lines.
    # A STEP entity starts with #NNN= and ends with ;
    # We'll process the file by reconstructing complete entities.
    
    lines = content.split('\n')
    result_lines = []
    entity_buffer = []
    in_data = False
    
    for line in lines:
        stripped = line.strip()
        
        if stripped == 'DATA;':
            in_data = True
            result_lines.append(line)
            continue
        
        if stripped == 'ENDSEC;' and in_data:
            # Flush any buffered entity
            if entity_buffer:
                entity_str = ' '.join(entity_buffer)
                entity_str = scale_entity(entity_str, factor)
                result_lines.append(entity_str)
                entity_buffer = []
            in_data = False
            result_lines.append(line)
            continue
        
        if not in_data:
            result_lines.append(line)
            continue
        
        # Inside DATA section
        if stripped.startswith('#') or entity_buffer:
            entity_buffer.append(line.rstrip('\r'))
            # Check if entity is complete (ends with ;)
            joined = ' '.join(entity_buffer)
            if ';' in joined:
                # Entity complete
                entity_str = joined
                entity_str = scale_entity(entity_str, factor)
                result_lines.append(entity_str)
                entity_buffer = []
        else:
            result_lines.append(line)
    
    # Flush remaining buffer
    if entity_buffer:
        entity_str = ' '.join(entity_buffer)
        entity_str = scale_entity(entity_str, factor)
        result_lines.append(entity_str)
    
    with open(dst_path, 'w', encoding='utf-8', newline='\r\n') as f:
        f.write('\n'.join(result_lines))


def scale_entity(entity: str, factor: float) -> str:
    """Apply all scaling transformations to a single STEP entity."""
    if 'CARTESIAN_POINT' in entity:
        entity = scale_cartesian_point(entity, factor)
    if 'CIRCLE' in entity and 'CIRCLE(' in entity:
        entity = scale_circle(entity, factor)
    if 'CYLINDRICAL_SURFACE' in entity:
        entity = scale_cylindrical_surface(entity, factor)
    if 'CONICAL_SURFACE' in entity:
        entity = scale_conical_surface(entity, factor)
    if 'VECTOR' in entity:
        entity = scale_vector(entity, factor)
    if 'LENGTH_MEASURE' in entity:
        entity = scale_uncertainty(entity, factor)
    if 'SPHERICAL_SURFACE' in entity:
        entity = scale_spherical_surface(entity, factor)
    if 'TOROIDAL_SURFACE' in entity:
        entity = scale_toroidal_surface(entity, factor)
    return entity


def main():
    factor = SCALE_FACTOR
    if len(sys.argv) > 1:
        try:
            factor = float(sys.argv[1])
        except ValueError:
            print(f"Invalid scale factor: {sys.argv[1]}")
            sys.exit(1)
    
    os.makedirs(DST_DIR, exist_ok=True)
    
    step_files = glob.glob(os.path.join(SRC_DIR, "*.step"))
    
    if not step_files:
        print("No .step files found in", SRC_DIR)
        sys.exit(1)
    
    print(f"Scaling {len(step_files)} STEP files by factor {factor}x")
    print(f"Output directory: {DST_DIR}")
    print()
    
    for src_path in sorted(step_files):
        filename = os.path.basename(src_path)
        dst_path = os.path.join(DST_DIR, filename)
        print(f"  Processing: {filename} ...", end=" ", flush=True)
        try:
            process_step_file(src_path, dst_path, factor)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
    
    print()
    print("Done!")


if __name__ == "__main__":
    main()
