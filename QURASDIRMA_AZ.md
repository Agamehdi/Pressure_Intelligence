# Daman Pressure Intelligence — Quraşdırma təlimatı

**Ümumi dizayn:** ağ fon, parlaq rənglər, Plotly qrafikləri. Real Excel dosyesi repoya daxil deyil: data məxfiliyini qorumaq üçün tətbiq daxilindən upload edilməlidir.

## GitHub

1. Bu ZIP faylını kompüterində çıxart.
2. GitHub-da yeni repository yarat.
3. ZIP-in içindəkiləri (`app.py`, `data_engine.py`, `requirements.txt`, `.streamlit`, `sample_data`, `tests` və s.) repository-yə yüklə.
4. `data/` qovluğuna real məlumatları **public** repoda yükləmə.
5. Streamlit Community Cloud-da **New app** → repository → main branch → `app.py` → **Deploy**.
6. Dashboard açılanda sol paneldə Excel-i upload et və `All Pressure Data` seç.

## Öz kompüterində

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Yeni funksiyalar

- 8 səhifə: Overview; Pressure & Depth; Time Trends; Well Explorer; Analytics Lab; Visualization Studio; Data Quality; Spotfire / Export.
- CSV/Excel input və metadata/QC işarələri; 5 rəng palitrası; font və ölçü parametrləri.
- PDF deyil, Spotfire import üçün uzun formatlı CSV-lər və summary CSV-lər.
- Süzgəclər, interactive hover/zoom/export, custom chart və pressure unit secondary axis.
- Save/load dashboard settings JSON.

**Vacib:** Real korporativ təzyiq məlumatlarını public Streamlit host-a göndərmək üçün əvvəlcə şirkətinizin informasiya təhlükəsizliyi qaydalarını yoxlayın. Tətbiq datası sessiya yaddaşında işləyir, lakin hostinq platformasının qaydaları ayrıca qiymətləndirilməlidir.


## FileNotFoundError düzəlişi (v2)

GitHub-a `sample_data` qovluğu yüklənməyibsə, əvvəlki versiya dayana bilərdi. Yeni versiya demo faylı olmadıqda **süni demo məlumatını avtomatik RAM-da yaradır**. Real məlumat üçün sol paneldən Excel yükləmək kifayətdir.

Mövcud GitHub repository-sində **hər iki faylı (`app.py` və `data_engine.py`) yenisi ilə əvəz et** və GitHub-a commit et. Streamlit Cloud avtomatik yenilənməlidir; lazım gələrsə, reboot et. `sample_data` qovluğunun olması artıq şərt deyil.
