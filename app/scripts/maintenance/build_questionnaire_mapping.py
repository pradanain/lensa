"""Build reviewed form mappings; source schemas/SQL are inspected, no answers read."""

import hashlib
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SQL_ROOT = ROOT / "app/sql/source_queries/02_Dataset_Siap_Analisis"

SOURCE_FILES = {
    "keluarga": "Keluarga/01_master_keluarga.sql",
    "anggota": "Keluarga/04_anggota_keluarga.sql",
    "perumahan": "Keluarga/02_keluarga_perumahan.sql",
    "aset_keluarga": "Keluarga/03_keluarga_ekonomi_aset.sql",
    "sosial_p0": "Keluarga/05_anggota_sosial_ekonomi.sql",
    "meteran": "Keluarga/06_meteran_pln.sql",
    "screening": "Keluarga/07_keluarga_screening_usaha.sql",
    "bku": "BKU/01_BKU_MASTER_SEMUA_STATUS.sql",
    "usaha": "Usaha_TGR/01_master_usaha.sql",
    "legalitas_usaha": "Usaha_TGR/02_usaha_pj_legalitas.sql",
    "kegiatan_usaha": "Usaha_TGR/03_usaha_kegiatan.sql",
    "digital_usaha": "Usaha_TGR/04_usaha_jaringan_digital.sql",
    "program_usaha": "Usaha_TGR/05_usaha_program_khusus.sql",
    "ekonomi_tahunan": "Usaha_TGR/06_usaha_ekonomi_tahunan.sql",
    "ekonomi_bulanan": "Usaha_TGR/07_ekonomi_bulanan_modal.sql",
    "jaringan_usaha": "Usaha_TGR/08A_usaha_jaringan.sql",
    "kantor_unit": "Usaha_TGR/08B_kantor_unit_roster.sql",
    "kantor_pusat": "Usaha_TGR/08C_kantor_pusat.sql",
    "p1_pekerjaan": "nested_dtsen/01_P1_ANGGOTA_PEKERJAAN_PENDAPATAN.sql",
    "p1_disabilitas": "nested_dtsen/02_P1_ANGGOTA_DISABILITAS.sql",
    "p1_kronis_a": "nested_dtsen/03_P1_ANGGOTA_PENYAKIT_KRONIS_A.sql",
    "p1_kronis_b": "nested_dtsen/04_P1_ANGGOTA_PENYAKIT_KRONIS_B.sql",
    "ub_a": "UB/09A_IDENTITAS_WILAYAH_KBLI_PJ.sql",
    "ub_b": "UB/09B_PEKERJA_EKONOMI_MODAL.sql",
    "ub_c": "UB/09C_DIGITAL_LINGKUNGAN_LEGALITAS.sql",
}


def projections(text):
    text = re.sub(
        r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|/\*.*?\*/|--[^\n]*",
        lambda m: " " if m[0].startswith(("/*", "--")) else m[0],
        text,
        flags=re.S,
    )
    depth = 0
    quote = None
    start = None
    end = None
    i = 0
    while i < len(text):
        char = text[i]
        if quote:
            if char == quote:
                if i + 1 < len(text) and text[i + 1] == quote:
                    i += 2
                    continue
                quote = None
        elif char in "'\"`":
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and (char.isalpha() or char == "_"):
            j = i + 1
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j].upper()
            if word == "SELECT" and start is None:
                start = j
            elif word == "FROM" and start is not None:
                end = i
                break
            i = j
            continue
        i += 1
    if start is None or end is None:
        raise ValueError("SOURCE_SELECT_NOT_FOUND")
    fields = []
    depth, quote, last = 0, None, start
    for i in range(start, end):
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            fields.append(text[last:i].strip())
            last = i + 1
    fields.append(text[last:end].strip())
    result = {}
    for expression in fields:
        match = re.search(r'(?:\bAS\s+|\.)[`"]?([A-Za-z_][A-Za-z0-9_]*)[`"]?\s*$', expression, re.I)
        if match:
            result[match[1]] = expression
    return result


def build():
    connection = sqlite3.connect((ROOT / "data/processed/se2026.sqlite").as_uri() + "?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    schemas = {
        sid: {r[1] for r in connection.execute('PRAGMA table_info("mart_' + sid + '")')}
        for sid in SOURCE_FILES
    }
    connection.close()
    proofs = {
        sid: projections((SQL_ROOT / name).read_text(encoding="utf-8-sig"))
        for sid, name in SOURCE_FILES.items()
    }
    mappings = {}

    def add(
        section, key, source, field, label=None, sensitive=False, display="text", visibility=None, note=None
    ):
        if field not in schemas[source] or field not in proofs[source]:
            raise ValueError("UNPROVEN_MAPPING: " + source + "." + field)
        if label and (label not in schemas[source] or label not in proofs[source]):
            raise ValueError("UNPROVEN_LABEL: " + source + "." + label)
        sql = SQL_ROOT / SOURCE_FILES[source]
        roster = (
            "businesses"
            if source
            in (
                "usaha",
                "legalitas_usaha",
                "kegiatan_usaha",
                "digital_usaha",
                "program_usaha",
                "ekonomi_tahunan",
                "ekonomi_bulanan",
                "jaringan_usaha",
            )
            else "members"
            if source
            in ("anggota", "sosial_p0", "p1_pekerjaan", "p1_disabilitas", "p1_kronis_a", "p1_kronis_b")
            else "meters"
            if source == "meteran"
            else "offices"
            if source == "kantor_unit"
            else None
        )
        mappings[(section, key)] = dict(
            source_object="mart_" + source,
            source_field=field,
            label_field=label,
            mapping_status="VERIFIED",
            converter=display,
            roster=roster,
            sensitive=sensitive,
            visibility_rule=visibility,
            note=note,
            evidence=dict(
                sql_path=sql.relative_to(ROOT).as_posix(),
                sql_sha256=hashlib.sha256(sql.read_bytes()).hexdigest(),
                expression=proofs[source][field],
                reference="DTD template 7.1.2 or supplied UB PDF; reviewed semantic correspondence",
            ),
        )

    def many(section, source, pairs, sensitive=False, display="text"):
        for pair in pairs.split():
            key, field = pair.split(":")
            add(section, key, source, field, sensitive=sensitive, display=display)

    many("b5", "keluarga", "no_kk:no_kk nik:nik_kk", True)
    many(
        "b5",
        "keluarga",
        "nama_kk:nama_kk no_bang:nomor_bangunan kode_bang:kode_penggunaan_bangunan jumlah_ak_kk:jumlah_anggota_sesuai_kk jumlah_ak:jumlah_anggota_listing jumlah_usaha_prelist:jumlah_usaha_prelist",
    )
    add("b5", "ada_keluarga", "keluarga", "kode_keberadaan_keluarga", "keberadaan_keluarga")
    add("b5", "ada_bang_usaha", "bku", "kode_keberadaan_bku", "keberadaan_bku")
    many("b5", "bku", "nama_usaha_bang:nama_bangunan_usaha")
    many(
        "b5",
        "screening",
        "usaha_kos:usaha_kos_kontrakan usaha_keliling:usaha_keliling usaha_online:usaha_online usaha_bongkar:usaha_bongkar_pasang usaha_konstruksi:usaha_konstruksi_penggalian usaha_lain:usaha_lainnya tanaman_pangan:usaha_tanaman_pangan hortikultura:usaha_hortikultura perkebunan:usaha_perkebunan peternakan:usaha_peternakan kehutanan:usaha_kehutanan perikanan:usaha_perikanan jasa_pertanian:usaha_jasa_pertanian",
    )
    many(
        "b_ak",
        "anggota",
        "no_urut_kk:nomor_urut_anggota nama_dtsen:nama_anggota umur_ak:umur art_ada_usaha:kode_memiliki_usaha",
    )
    many(
        "b_ak",
        "anggota",
        "nik_dtsen:nik_anggota tgl_lahir:tanggal_lahir_hari bln_lahir:bulan_lahir thn_lahir:tahun_lahir",
        True,
    )
    for key, field, label in [
        ("hubungan", "kode_hubungan", "hubungan_kepala_keluarga"),
        ("keberadaan_dtsen", "kode_keberadaan_anggota", "keberadaan_anggota"),
        ("status_kawin", "kode_status_perkawinan", "status_perkawinan"),
        ("jk_dtsen", "kode_jenis_kelamin", "jenis_kelamin"),
    ]:
        add("b_ak", key, "anggota", field, label)
    many(
        "b_ak",
        "anggota",
        "prov_dn:provinsi_domisili kab_dn:kabupaten_domisili domisili_ln:negara_domisili_luar_negeri",
    )
    many(
        "blokl",
        "usaha",
        "nama_usaha:nama_usaha nama_komersial:nama_komersial no_usaha:nomor_usaha no_bang_l:nomor_bangunan jenis_usaha:jenis_usaha keg_utama:kegiatan_utama produk:produk_utama kategori:kategori kbli:kbli",
    )
    many("blokl", "usaha", "alamat_usaha_var:alamat_usaha", True)
    add("blokl", "keberadaan_usaha", "usaha", "kode_keberadaan_usaha", "keberadaan_usaha")
    many(
        "blokl",
        "legalitas_usaha",
        "website:website jenis_kawasan:jenis_kawasan nama_kek_ki:kode_nama_kek_ki nama_kawasan:nama_kawasan punya_nib:punya_nib tidak_nib:alasan_tidak_punya_nib badan_usaha:badan_usaha koperasi_kdkmp:koperasi_kdkmp jenis_koperasi:jenis_koperasi lap_keuangan:mempunyai_laporan_keuangan pengusaha:nama_pengusaha_pj jk:jenis_kelamin_pj umur:umur_pj",
    )
    many(
        "blokl",
        "legalitas_usaha",
        "nib:nib nib_lainnya:alasan_nib_lainnya email:email hp:nomor_hp_whatsapp no_telp:nomor_telepon nik_pengusaha:nik_pengusaha_pj",
        True,
    )
    many(
        "blokl",
        "kegiatan_usaha",
        "produk_sendiri:memproduksi_barang layanan_mamin:layanan_makan_minum keg_penjualan:melakukan_penjualan_barang keg_jasa:aktivitas_jasa lokasi_usaha:lokasi_kegiatan_usaha",
    )
    add("blokl", "jaringan", "digital_usaha", "kode_jaringan_usaha", "jaringan_usaha")
    add("blokl", "internet", "digital_usaha", "kode_menggunakan_internet", "menggunakan_internet")
    many(
        "blokl",
        "digital_usaha",
        "jumlah_kc:jumlah_kantor_cabang_unit nama_kp:nama_kantor_pusat negara_kp:kode_negara_kantor_pusat prov_kp:kode_provinsi_kantor_pusat kab_kp:kode_kabupaten_kantor_pusat digital:teknologi_digital",
    )
    for key, field in [
        ("internet_pesanan", "internet_menerima_pesanan"),
        ("internet_produksi", "internet_produksi"),
        ("internet_distribusi", "internet_distribusi"),
        ("internet_beli", "internet_pembelian_bahan_baku"),
        ("internet_promosi", "internet_promosi"),
        ("internet_lainnya", "internet_lainnya"),
    ]:
        add(
            "blokl",
            key,
            "digital_usaha",
            field,
            visibility=dict(
                source="digital_usaha", field="kode_menggunakan_internet", not_applicable_values=["2"]
            ),
        )
    many(
        "blokl",
        "program_usaha",
        "produksi_lingkungan:memproduksi_produk_ramah_lingkungan perlindungan_lingkungan:menggunakan_input_perlindungan_lingkungan produk_seni:menggunakan_produk_seni_budaya_teknologi halal:mempunyai_produk_bersertifikat_halal sudah_halal:jumlah_varian_sudah_halal belum_halal:jumlah_varian_belum_halal izin_edar:mempunyai_izin_edar sudah_bpom:jumlah_varian_sudah_bpom belum_bpom:jumlah_varian_belum_bpom mitra_kdkmp:bermitra_kdkmp peran_mbg:terlibat_program_mbg barang_non_pddk:transaksi_barang_nonpenduduk jasa_non_pddk:penjualan_jasa_nonpenduduk beli_jasa_non_pddk:pembelian_jasa_nonpenduduk tk_laki:pekerja_laki_laki tk_pr:pekerja_perempuan total_tk_jk:total_pekerja_jenis_kelamin tk_dibayar:pekerja_dibayar tk_tdk_dibayar:pekerja_tidak_dibayar total_tk_bayar:total_pekerja_status_bayar tahun_operasi:tahun_mulai_operasi",
    )
    many(
        "blokl",
        "ekonomi_tahunan",
        "gaji:pengeluaran_gaji_jaminan_sosial biaya_produksi:biaya_produksi biaya_pembelian:biaya_pembelian_barang_terjual operasional:biaya_operasional non_operasional:biaya_non_operasional total_pengeluaran:total_pengeluaran_2025 nilai_pendapatan:pendapatan_utama_2025 pendapatan_lain:pendapatan_lainnya_2025 total_pendapatan:total_pendapatan_2025 pendapatan_online:persen_pendapatan_online aset_usaha_thn:aset_tanah_bangunan_2025 aset_lain_thn:aset_selain_tanah_bangunan_2025 total_aset_thn:total_aset_2025 rentang_aset_thn:rentang_aset_2025 luas_tanah_thn:luas_tanah_usaha_m2",
        True,
        "decimal",
    )
    many(
        "blokl",
        "ekonomi_bulanan",
        "gaji_bln:pengeluaran_gaji_jaminan_sosial_bln biaya_produksi_bln:biaya_produksi_bln biaya_pembelian_bln:biaya_pembelian_barang_terjual_bln operasional_bln:biaya_operasional_bln non_operasional_bln:biaya_non_operasional_bln total_pengeluaran_bln:total_pengeluaran_bln nilai_pendapatan_bln:pendapatan_utama_bln pendapatan_lain_bln:pendapatan_lainnya_bln total_pendapatan_bln:total_pendapatan_bln pendapatan_online_bln:persen_pendapatan_online_bln aset_tanah_bln:aset_tanah_bangunan_bln aset_lain_bln:aset_selain_tanah_bangunan_bln total_aset_bln:total_aset_bln luas_tanah_bln:luas_tanah_usaha_m2 pribadi_didirikan:modal_pribadi_persen nonprofit_didirikan:modal_nonprofit_persen publik_didirikan:modal_korporasi_publik_persen nonpublik_didirikan:modal_korporasi_nonpublik_persen pemerintah_didirikan:modal_pemerintah_persen asing_didirikan:modal_asing_persen",
        True,
        "decimal",
    )
    many(
        "blokl",
        "kantor_unit",
        "kp_unit:nama_kantor_unit kp_jenis:jenis_unit kp_prov:provinsi_unit kp_kab:kabupaten_unit kp_tk:jumlah_pekerja_unit_2025",
    )
    many(
        "blokl",
        "kantor_unit",
        "kp_total_pengeluaran:pengeluaran_unit_2025 kp_total_pendapatan:pendapatan_unit_2025 kp_total_aset:aset_unit_2025",
        True,
        "decimal",
    )
    many(
        "b_ak_lanjutan",
        "keluarga",
        "dtsen_nama_kk:nama_kk jml_kk:jumlah_anggota_sesuai_kk jml_kk_update:jumlah_anggota_hasil_pendataan",
    )
    many("b_ak_lanjutan", "keluarga", "nik_kk:nik_kk dtsen_no_kk:no_kk", True)
    add("b_ak_lanjutan", "sekolah", "sosial_p0", "kode_partisipasi_sekolah", "partisipasi_sekolah")
    add(
        "b_ak_lanjutan",
        "ijazah",
        "sosial_p0",
        "kode_ijazah_tertinggi",
        "ijazah_tertinggi",
        visibility=dict(source="anggota", field="umur", minimum_age=5),
    )
    add(
        "b_ak_lanjutan",
        "profesi",
        "sosial_p0",
        "kode_profesi_utama",
        "profesi_utama",
        visibility=dict(source="anggota", field="umur", minimum_age=10),
    )
    many(
        "b_ak_lanjutan",
        "p1_pekerjaan",
        "profesi_lainnya:profesi_lainnya status_kerja:status_kerja_label pendapatan_pekerjaan:pendapatan_pekerjaan_label pendapatan_usaha:pendapatan_usaha_label pend_usaha_lain:pend_usaha_lain_label rekening:rekening_label",
    )
    many(
        "b_ak_lanjutan",
        "sosial_p0",
        "pend_gaji:pendapatan_gaji pend_tunjangan:pendapatan_tunjangan pend_uangmkn:pendapatan_uang_makan pend_honor:pendapatan_honor pend_lembur:pendapatan_lembur pend_lainnya:pendapatan_pekerjaan_lainnya pend_usaha:total_pendapatan_usaha nilai_pend_lain:total_pendapatan_lain",
        True,
        "decimal",
    )
    # The identically named P1 field is opaque text; do not use it for this sum.
    add(
        "b_ak_lanjutan",
        "nilai_pend_pekerjaan",
        "sosial_p0",
        "total_pendapatan_pekerjaan",
        sensitive=True,
        display="decimal",
        note="Numerik dari P0 saja; kolom P1 dengan nama serupa tidak menjadi nilai uang.",
    )
    for key in ["dis_fisik", "dis_mental", "dis_intelek", "dis_netra", "dis_rungu", "dis_wicara"]:
        add("b_ak_lanjutan", key, "p1_disabilitas", key + "_value", key + "_label", sensitive=True)
    for source, keys in [
        ("p1_kronis_a", "hipertensi rematik asma jantung diabetes tbc stroke kanker hemofilia ginjal"),
        ("p1_kronis_b", "hiv kolestrol sirosis talasemia leukemia alzheimer lainnya"),
    ]:
        for key in keys.split():
            add(
                "b_ak_lanjutan",
                "sakit_" + key,
                source,
                "sakit_" + key + "_value",
                "sakit_" + key + "_label",
                sensitive=True,
            )
    many(
        "b_perumahan",
        "perumahan",
        "jns_bangunan:jenis_bangunan jns_bangunan_lain:jenis_bangunan_lainnya nm_apt:nama_apartemen_rusun status_kepemilikan:status_kepemilikan bukti_kepemilikan:bukti_kepemilikan luas_lantai:luas_lantai jns_lantai:jenis_lantai kondisi_lantai:kondisi_lantai jns_dinding:jenis_dinding kondisi_dinding:kondisi_dinding jns_atap:jenis_atap kondisi_atap:kondisi_atap tempat_bab:fasilitas_bab jns_closet:jenis_kloset buang_tinja:pembuangan_akhir_tinja air_minum:sumber_air_minum sumber_penerangan:sumber_penerangan jml_meteran:jumlah_meteran",
    )
    many(
        "b_perumahan",
        "perumahan",
        "sewa_sendiri:sewa_sendiri sewa_kontrak:sewa_kontrak sewa_dinas:sewa_dinas listrik_sebulan:pengeluaran_listrik_sebulan pulsa_sebulan:pengeluaran_pulsa_internet_sebulan",
        True,
        "decimal",
    )
    add("b_perumahan", "daya_terpasang", "meteran", "kode_daya_terpasang", "daya_terpasang")
    add("b_perumahan", "id_pln_pilih", "meteran", "kode_jenis_identitas_pln", "jenis_identitas_pln")
    many("b_perumahan", "meteran", "id_pelanggan:id_pelanggan_pln no_meteran:nomor_meteran", True)
    many(
        "b_perumahan",
        "aset_keluarga",
        "pengeluaran_makanan_mingguan:pengeluaran_makanan_mingguan pengeluaran_non_makan_bulanan:pengeluaran_non_makan_bulanan pengeluaran_non_makan_tahunan:pengeluaran_non_makan_tahunan total_pendapatan_keluarga_sebulan_tampil:total_pendapatan_keluarga_sebulan total_pengeluaran_keluarga_sebulan_tampil:total_pengeluaran_keluarga_sebulan nilai_motor:nilai_aset_sepeda_motor nilai_mobil:nilai_aset_mobil nilai_lahan:nilai_aset_lahan_lain nilai_rumah:nilai_aset_rumah_bangunan_lain",
        True,
        "decimal",
    )
    many(
        "b_perumahan",
        "aset_keluarga",
        "jumlah_tabung3kg_new:jumlah_tabung_lpg_3kg jumlah_tabung5kg_new:jumlah_tabung_lpg_5kg_lebih jumlah_kulkas_new:jumlah_kulkas jumlah_ac_new:jumlah_ac jumlah_emas_new:jumlah_emas_gram jumlah_laptop_new:jumlah_komputer_laptop_tablet jumlah_motor_new:jumlah_sepeda_motor jumlah_mobil_new:jumlah_mobil jumlah_lahan_new:jumlah_lahan_lain jumlah_rumah_new:jumlah_rumah_bangunan_lain",
    )
    template = json.loads(
        (ROOT / "codex_app_brief/referensi/DTD/DTD_FORM_STRUCTURE.json").read_text(encoding="utf-8")
    )
    dtd = []
    excluded = {
        "is_new",
        "pilih_umkm",
        "callnik_button",
        "callnik_button_l",
        "callnik_button_p",
        "cek_nib",
        "genai_button",
        "file_input",
        "pilih_keluarga_sls",
        "alamat_sesuai",
        "nama_usaha_edit",
        "nama_dtsen_edit",
        "pengusaha_var",
        "jk_var",
        "umur_pj_var",
        "nik_pengusaha_var",
        "jml_kk_asgbaru",
        "apakah_usaha",
        "apakah_ak",
    }
    for section in template["sections"]:
        fields = []
        seen = set()
        for item in section["fields"]:
            key = item["data_key"]
            label = item["question_label"]
            mapped = mappings.get((section["section_key"], key))
            visible = mapped or (
                item["type_code"] in [20, 24, 25, 26, 27, 28, 30, 35, 38]
                and not item["has_children"]
                and key not in excluded
                and not key.startswith(("cek_", "set_", "flag_"))
                and "New Question" not in label
                and not label.startswith("[HTML")
            )
            if not visible or key in seen:
                continue
            seen.add(key)
            field = dict(
                question_id=section["section_key"] + "." + key,
                question_text=re.sub(r"\$[A-Za-z_]+\$?", "responden", label),
                template_key=key,
                source_object=None,
                source_field=None,
                mapping_status="UNVERIFIED",
                converter="text",
                sensitive=False,
                roster=None,
                visibility_rule=None,
            )
            if section["section_key"] in ["b0", "ket_jawaban", "cat", "anomali_section", "anomali_keluarga"]:
                field["mapping_status"] = "NOT_EXPORTED"
            if mapped:
                field.update(mapped)
            fields.append(field)
        if not fields:
            fields = [
                dict(
                    question_id=section["section_key"] + ".unavailable",
                    question_text="Rincian bagian ini tidak tersedia dalam ekspor lokal.",
                    source_object=None,
                    source_field=None,
                    mapping_status="NOT_EXPORTED",
                    converter="text",
                    sensitive=False,
                    roster=None,
                    visibility_rule=None,
                )
            ]
        dtd.append(dict(section_id=section["section_key"], title=section["section_label"], questions=fields))

    ub = []
    groups = [
        ("ub_i_1", "Blok I · Identitas perusahaan (r1–9)", 1),
        ("ub_i_2", "Blok I · Jaringan dan digital (r10–19)", 4),
        ("ub_i_3", "Blok I · Pekerja dan ekonomi (r20–25)", 6),
        ("ub_ii", "Blok II · Catatan", 8),
        ("ub_iii", "Blok III · Pemberi jawaban", 8),
    ]
    ub_groups = {
        key: dict(section_id=key, title=title, pdf_page=page, questions=[]) for key, title, page in groups
    }

    def uq(group, number, text, source=None, field=None, sensitive=False, display="text", visibility=None):
        result = dict(
            question_id="ub." + number,
            question_text=number + ". " + text,
            source_object=None,
            source_field=None,
            mapping_status="NOT_EXPORTED",
            converter=display,
            sensitive=sensitive,
            roster=None,
            visibility_rule=visibility,
        )
        if source:
            add("_ub", number, source, field, sensitive=sensitive, display=display, visibility=visibility)
            result.update(mappings[("_ub", number)])
        ub_groups[group]["questions"].append(result)

    for number, text, source, field, sensitive in [
        ("1", "Provinsi", None, None, False),
        ("2", "Kabupaten/Kota", None, None, False),
        ("3", "Kecamatan", "ub_a", "kecamatan", False),
        ("4", "Desa/Kelurahan", "ub_a", "desa_kelurahan", False),
        ("5a", "Nama perusahaan", "ub_a", "nama_usaha", False),
        ("5b", "Nama komersial", "ub_a", "nama_komersial", False),
        ("5c", "Alamat perusahaan", "ub_a", "alamat_usaha", True),
        ("5d", "Jenis kawasan", "ub_c", "jenis_kawasan", False),
        ("5e", "Nama kawasan", "ub_c", "nama_kawasan", False),
        ("6a", "Apakah memiliki NIB?", "ub_c", "memiliki_nib", False),
        ("6b", "Nomor Induk Berusaha", "ub_a", "nib", True),
        ("6c", "Alasan tidak memiliki NIB", "ub_c", "alasan_tanpa_nib", False),
        ("7a", "Status badan usaha", "ub_a", "badan_usaha", False),
        ("7b", "Apakah koperasi ini KDKMP?", None, None, False),
        ("7c", "Jenis koperasi", None, None, False),
        ("7d", "Mempunyai laporan/catatan keuangan", "ub_b", "memiliki_catatan_keuangan", False),
        ("8a", "Nama pengusaha/penanggung jawab", "ub_a", "nama_penanggung_jawab", False),
        ("8b", "Jenis kelamin penanggung jawab", "ub_a", "jenis_kelamin_penanggung_jawab", False),
        ("8c", "Umur penanggung jawab", "ub_a", "umur_penanggung_jawab", False),
        ("8d", "NIK penanggung jawab", "ub_a", "nik_penanggung_jawab", True),
        ("9a", "Kegiatan utama", "ub_a", "kegiatan_utama", False),
        ("9b1", "Memproduksi barang di lokasi ini", "ub_c", "produksi_barang_di_lokasi", False),
        ("9b2", "Layanan makan/minum", None, None, False),
        ("9b3", "Penjualan barang", None, None, False),
        ("9b4", "Aktivitas jasa/pertanian", None, None, False),
        ("9c", "Lokasi kegiatan", None, None, False),
        ("9d", "Input usaha", None, None, False),
        ("9e", "Proses usaha", None, None, False),
        ("9f", "Produk utama", "ub_a", "produk_utama", False),
        ("9g", "Kode KBLI", "ub_a", "kbli_akhir", False),
        ("9h", "Kategori lapangan usaha", "ub_a", "kategori_kbli", False),
        ("9i", "Klasifikasi akomodasi", None, None, False),
    ]:
        uq("ub_i_1", number, text, source, field, sensitive)
    for number, text, source, field in [
        ("10a", "Jaringan usaha", "ub_a", "jaringan_usaha"),
        ("10b", "Jumlah kantor cabang/unit", "ub_c", "jumlah_kantor_cabang"),
        ("11a", "Nama kantor pusat", "ub_a", "nama_kantor_pusat"),
        ("11b", "Alamat kantor pusat", "ub_a", "alamat_kantor_pusat"),
        ("11d", "Negara kantor pusat", "ub_c", "negara_kantor_pusat"),
        ("12a", "Menggunakan internet", "ub_c", "menggunakan_internet"),
        ("12b1", "Internet untuk pesanan", "ub_c", "internet_pesanan"),
        ("12b2", "Internet untuk produksi", "ub_c", "internet_produksi"),
        ("12b3", "Internet untuk distribusi", "ub_c", "internet_distribusi"),
        ("12b4", "Internet untuk pembelian", "ub_c", "internet_pembelian"),
        ("12b5", "Internet untuk promosi", "ub_c", "internet_promosi"),
        ("12b6", "Internet tujuan lain", None, None),
        ("12c", "Memanfaatkan teknologi digital", "ub_c", "memanfaatkan_teknologi_digital"),
        ("13a", "Produk ramah lingkungan", "ub_c", "menghasilkan_produk_ramah_lingkungan"),
        ("13b", "Input untuk perlindungan lingkungan", "ub_c", "perlindungan_lingkungan"),
        ("14", "Penggunaan produk seni/budaya", "ub_c", "penggunaan_produk_seni_budaya"),
        ("15a", "Produk bersertifikat halal", "ub_c", "produk_bersertifikat_halal"),
        ("15b", "Varian bersertifikat halal", None, None),
        ("15c", "Varian belum halal", None, None),
        ("16a", "Memiliki izin edar", "ub_c", "memiliki_izin_edar"),
        ("16b", "Varian berizin edar", None, None),
        ("16c", "Varian belum berizin", None, None),
        ("17", "Kemitraan KDKMP", "ub_c", "kemitraan_kdkmp"),
        ("18", "Keterlibatan MBG", "ub_c", "keterlibatan_mbg"),
        ("19a", "Transaksi barang nonpenduduk", None, None),
        ("19b", "Penjualan jasa nonpenduduk", None, None),
        ("19c", "Pembelian jasa nonpenduduk", None, None),
    ]:
        visibility = (
            dict(source="ub_c", field="menggunakan_internet", not_applicable_values=["2"])
            if number.startswith("12b")
            else None
        )
        uq("ub_i_2", number, text, source, field, number == "11b", visibility=visibility)
    for number, text, source, field, display in [
        ("20a", "Pekerja laki-laki", "ub_b", "pekerja_laki_laki", "decimal"),
        ("20b", "Pekerja perempuan", "ub_b", "pekerja_perempuan", "decimal"),
        ("20c", "Total pekerja", "ub_b", "jumlah_pekerja", "decimal"),
        ("21", "Tahun mulai beroperasi", "ub_b", "tahun_operasi", "text"),
        ("22a", "Upah/gaji dan jaminan sosial", "ub_b", "gaji_dan_jaminan_sosial", "decimal"),
        ("22b", "Biaya produksi", "ub_b", "biaya_produksi", "decimal"),
        ("22c", "Biaya pembelian barang", "ub_b", "biaya_pembelian_barang", "decimal"),
        ("22d", "Biaya operasional", "ub_b", "biaya_operasional", "decimal"),
        ("22e", "Biaya nonoperasional", "ub_b", "biaya_non_operasional", "decimal"),
        ("22f", "Total pengeluaran", "ub_b", "total_pengeluaran", "decimal"),
        ("23a", "Pendapatan utama", "ub_b", "pendapatan_utama", "decimal"),
        ("23b", "Pendapatan lainnya", "ub_b", "pendapatan_lainnya", "decimal"),
        ("23c", "Total pendapatan", "ub_b", "total_pendapatan", "decimal"),
        ("23d", "Persentase pendapatan online", "ub_c", "persentase_pendapatan_online", "decimal"),
        ("24a", "Aset tanah/bangunan", "ub_b", "aset_tanah_bangunan", "decimal"),
        ("24b", "Aset selain tanah/bangunan", "ub_b", "aset_selain_tanah_bangunan", "decimal"),
        ("24c", "Total aset", "ub_b", "total_aset", "decimal"),
        ("24c1", "Rentang aset", None, None, "text"),
        ("24d", "Luas tanah", "ub_b", "luas_tanah_m2", "decimal"),
        ("25a", "Modal pribadi", "ub_b", "modal_pribadi_persen", "decimal"),
        ("25b", "Modal nonprofit", "ub_b", "modal_nonprofit_persen", "decimal"),
        ("25c", "Modal korporasi publik", "ub_b", "modal_korporasi_publik_persen", "decimal"),
        ("25d", "Modal korporasi nonpublik", "ub_b", "modal_korporasi_nonpublik_persen", "decimal"),
        ("25e", "Modal pemerintah", "ub_b", "modal_pemerintah_persen", "decimal"),
        ("25f", "Modal asing", "ub_b", "modal_asing_persen", "decimal"),
    ]:
        uq("ub_i_3", number, text, source, field, number.startswith(("22", "23", "24", "25")), display)
    uq("ub_ii", "II", "Catatan")
    for number, text in [
        ("III.1", "Nama pemberi jawaban"),
        ("III.2", "NIP/NMS petugas"),
        ("III.3", "Nomor telepon"),
        ("III.4", "Email"),
        ("III.5", "Tanggal pelaksanaan"),
        ("III.6", "Tanda tangan"),
    ]:
        uq("ub_iii", number, text)
    ub = list(ub_groups.values())
    output = ROOT / "app/config/questionnaires"
    output.mkdir(parents=True, exist_ok=True)
    for name, sections in [("dtd", dtd), ("ub", ub)]:
        for section in sections:
            for field in section["questions"]:
                source = (field.get("source_object") or "").removeprefix("mart_")
                field["period"] = (
                    "ANNUAL_2025"
                    if source == "ekonomi_tahunan"
                    else "LAST_MONTH_NEW_2026_CALENDAR_MONTH_UNAVAILABLE"
                    if source == "ekonomi_bulanan"
                    else "UB_FORM_2025_EXPORT_PERIOD_UNVERIFIED"
                    if source == "ub_b"
                    else "LOCAL_SNAPSHOT"
                )
                if field["converter"] == "decimal":
                    field["unit"] = "SOURCE_UNIT_UNVERIFIED" if field.get("sensitive") else "SOURCE_COUNT"
        (output / (name + ".json")).write_text(
            json.dumps(
                dict(
                    form=name,
                    reference="Supplied DTD template 7.1.2" if name == "dtd" else "Supplied UB PDF, 8 pages",
                    sections=sections,
                ),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    counts = {
        name: dict(
            sections=len(sections),
            questions=sum(len(s["questions"]) for s in sections),
            verified=sum(f["mapping_status"] == "VERIFIED" for s in sections for f in s["questions"]),
        )
        for name, sections in [("dtd", dtd), ("ub", ub)]
    }
    print(json.dumps(counts))


if __name__ == "__main__":
    build()
