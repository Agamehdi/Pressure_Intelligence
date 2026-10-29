# Daman Pressure Intelligence — V3 / GitHub və Streamlit Cloud

## Nə dəyişdi?

- Açılış ekranı **boşdur**: heç bir demo və ya sintetik məlumat yüklənmir.
- Sol paneldən XLSX, XLSM və ya CSV yüklədikdə bütün 8 analitik bölmə aktivləşir.
- Streamlit-in öz light theme-i və standart ikonları istifadə olunur. Əvvəl görünən `keyboard_double_arrow...` və `upload` kimi yazılar artıq çıxmamalıdır; ikon fontunu pozan ümumi CSS ləğv edildi.
- Mövcud vizual üslub, Plotly qrafikləri, filtrlər, rəng palitraları, QC və Spotfire export saxlanılıb.

## GitHub-da mövcud V2 tətbiqini yenilə

1. Ən asan yol: **Daman_V3_Fix_Only.zip** içindəki `app.py` və `data_engine.py` fayllarını GitHub repo-nun kökündəki fayllarla əvəz et.
2. **Commit changes** et.
3. Streamlit Cloud-da tətbiqi yenilə / lazım olsa **Manage app → Reboot app** et.
4. İstəsən, köhnə `sample_data/` qovluğunu sil: yeni proqram ondan istifadə etmir.
5. Sol paneldən `Daman_Pressure_Data_Compiled.xlsx` yüklə, `All Pressure Data` sheet-ini seç.

## Sıfırdan deployment

1. **Daman_Pressure_Intelligence_v3_GitHub_Ready.zip** içindəkiləri (ZIP-in özünü deyil) yeni GitHub repo-suna yüklə.
2. Streamlit Community Cloud → New app → repo/branch → **Main file path: `app.py`**.
3. Deploy, sonra Excel/CSV-ni tətbiq daxilindən yüklə.

Local run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Testlər:

```bash
python -m unittest discover -s tests -v
```

**Məxfilik:** Korporativ reservoir/pressure məlumatlarını public GitHub repository-yə qoyma. Tətbiqin hansı serverə yükləmə apardığını və həmin hostinqin şirkət qaydalarına uyğunluğunu əvvəlcədən yoxla.
