"""Viewer field permissions and directory address display."""

VIEWER_FIELDS = {
    ("mart_keluarga", "alamat_keluarga"),
    ("mart_bku", "alamat_prelist"),
    ("mart_bku", "jalan_domisili"),
    ("mart_usaha", "alamat_usaha"),
    ("mart_legalitas_usaha", "nomor_telepon"),
    ("mart_legalitas_usaha", "nomor_hp_whatsapp"),
    ("mart_ub_a", "alamat_usaha"),
    ("mart_ub_a", "nomor_hp_usaha"),
    ("mart_ekonomi_tahunan", "pendapatan_utama_2025"),
    ("mart_ekonomi_bulanan", "pendapatan_utama_bln"),
    ("mart_ub_b", "pendapatan_utama"),
}


def viewer_field_allowed(field):
    return (field.get("source_object"), field.get("source_field")) in VIEWER_FIELDS


def full_address(street, village, district):
    """Append known assignment labels to a source address; never invent a street."""
    street = str(street or "").strip()
    if not street:
        return None
    parts = [street]
    for prefix, value in [("Desa/Kelurahan", village), ("Kecamatan", district)]:
        value = str(value or "").strip()
        if value and value.casefold() not in ", ".join(parts).casefold():
            parts.append(f"{prefix} {value}")
    return ", ".join(parts)
