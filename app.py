import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from utils.data_processor import DataProcessor
from utils.member_manager import MemberManager
from utils.report_generator import ReportGenerator

# Streamlit sayfa konfigürasyonu
st.set_page_config(
    page_title="BTag Affiliate Takip Sistemi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("📊 BTag Affiliate Takip Sistemi")
    st.markdown("---")
    
    # Utility sınıflarını başlat
    data_processor = DataProcessor()
    member_manager = MemberManager()
    report_generator = ReportGenerator()
    
    # Sidebar - Ana menü
    st.sidebar.title("📋 Menü")
    menu = st.sidebar.selectbox(
        "İşlem Seçin",
        ["Ana Sayfa", "Excel Yükleme", "Üye Yönetimi", "Raporlar", "İstatistikler"]
    )
    
    if menu == "Ana Sayfa":
        show_dashboard(member_manager, report_generator)
    elif menu == "Excel Yükleme":
        show_excel_upload(data_processor, member_manager)
    elif menu == "Üye Yönetimi":
        show_member_management(member_manager)
    elif menu == "Raporlar":
        show_reports(report_generator, member_manager)
    elif menu == "İstatistikler":
        show_statistics(report_generator, member_manager)

def show_dashboard(member_manager, report_generator):
    st.header("🏠 Ana Sayfa")
    
    # Mevcut ay bilgisi
    current_month = datetime.now().strftime("%Y-%m")
    st.subheader(f"📅 Mevcut Ay: {datetime.now().strftime('%B %Y')}")
    
    # Üye sayısı
    members = member_manager.get_active_members()
    total_members = len(members)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("👥 Toplam Üye", total_members)
    
    with col2:
        # Bu ay kaydedilmiş veri var mı kontrol et
        monthly_data = report_generator.get_monthly_summary(current_month)
        if monthly_data:
            total_deposits = sum([m.get('total_deposits', 0) for m in monthly_data])
            st.metric("💰 Bu Ay Toplam Yatırım", f"{total_deposits:,.2f} TL")
        else:
            st.metric("💰 Bu Ay Toplam Yatırım", "0.00 TL")
    
    with col3:
        if monthly_data:
            total_withdrawals = sum([m.get('total_withdrawals', 0) for m in monthly_data])
            st.metric("💸 Bu Ay Toplam Çekim", f"{total_withdrawals:,.2f} TL")
        else:
            st.metric("💸 Bu Ay Toplam Çekim", "0.00 TL")
    
    st.markdown("---")
    
    # Son işlemler
    st.subheader("📊 Son İşlemler")
    if monthly_data:
        df_summary = pd.DataFrame(monthly_data)
        if not df_summary.empty:
            # Son 10 üyeyi göster
            df_display = df_summary.head(10).copy()
            df_display['Net Toplam'] = df_display['total_deposits'] - df_display['total_withdrawals']
            
            # Renk kodlaması için stil uygula
            def color_net_total(val):
                if val > 0:
                    return 'color: green'
                elif val < 0:
                    return 'color: red'
                else:
                    return 'color: black'
            
            styled_df = df_display[['member_name', 'total_deposits', 'total_withdrawals', 'Net Toplam']].style.map(
                color_net_total, subset=['Net Toplam']
            )
            
            st.dataframe(styled_df, use_container_width=True)
        else:
            st.info("Bu ay henüz kayıt bulunmuyor.")
    else:
        st.info("Bu ay henüz kayıt bulunmuyor.")

def show_excel_upload(data_processor, member_manager):
    st.header("📤 Excel Dosyası Yükleme")
    
    # BTag girişi
    btag_input = st.text_input("🏷️ BTag Numarası", placeholder="Örnek: 2424878")
    
    # Excel dosyası yükleme
    uploaded_file = st.file_uploader(
        "📁 Players Report Excel Dosyasını Seçin",
        type=['xlsx', 'xls'],
        help="players-report.xlsx formatında dosya yükleyin"
    )
    
    if uploaded_file and btag_input:
        try:
            # Excel dosyasını oku
            df = pd.read_excel(uploaded_file)
            st.success(f"✅ Excel dosyası başarıyla yüklendi! {len(df)} satır bulundu.")
            
            # Veri önizleme
            with st.expander("📋 Veri Önizleme"):
                st.dataframe(df.head(), use_container_width=True)
            
            # BTag'e göre filtrele
            if 'BTag' in df.columns:
                filtered_df = df[df['BTag'].astype(str) == str(btag_input)]
                st.info(f"🎯 BTag {btag_input} için {len(filtered_df)} kayıt bulundu.")
                
                if len(filtered_df) > 0:
                    # Veriyi işle
                    processed_data = data_processor.process_excel_data(filtered_df)
                    
                    # Yeni üye kontrolü
                    current_members = member_manager.get_all_members()
                    current_member_ids = [str(m['member_id']) for m in current_members]
                    
                    new_members = []
                    for _, row in processed_data.iterrows():
                        if str(row['member_id']) not in current_member_ids:
                            new_members.append({
                                'member_id': str(row['member_id']),
                                'username': row['username'],
                                'full_name': row['customer_name']
                            })
                    
                    if new_members:
                        st.warning(f"🆕 {len(new_members)} yeni üye bulundu!")
                        
                        # Yeni üyeleri göster
                        new_members_df = pd.DataFrame(new_members)
                        st.dataframe(new_members_df, use_container_width=True)
                        
                        if st.button("➕ Yeni Üyeleri Ekle"):
                            for member in new_members:
                                member_manager.add_member(
                                    member['member_id'],
                                    member['username'],
                                    member['full_name']
                                )
                            st.success("✅ Yeni üyeler başarıyla eklendi!")
                            st.rerun()
                    
                    # İşlenmiş veriyi göster
                    st.subheader("📊 İşlenmiş Veriler")
                    
                    # Net toplam hesapla ve renk kodlaması ekle
                    display_df = processed_data.copy()
                    display_df['Toplam'] = display_df['total_deposits'] - display_df['total_withdrawals']
                    
                    # Renk kodlaması için CSS
                    def highlight_totals(val):
                        if val > 0:
                            return 'background-color: lightgreen'
                        elif val < 0:
                            return 'background-color: lightcoral'
                        else:
                            return 'background-color: lightgray'
                    
                    styled_df = display_df.style.map(highlight_totals, subset=['Toplam'])
                    st.dataframe(styled_df, use_container_width=True)
                    
                    # Tarih seçimi ve kaydetme
                    st.subheader("💾 Kayıt İşlemi")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        selected_date = st.date_input(
                            "📅 Kayıt Tarihi",
                            value=datetime.now(),
                            help="Verilerin hangi tarihe kaydedileceğini seçin"
                        )
                    
                    with col2:
                        if st.button("💾 Kaydet", type="primary"):
                            # Veriyi kaydet
                            success = data_processor.save_daily_data(
                                processed_data, 
                                btag_input, 
                                selected_date
                            )
                            
                            if success:
                                st.success("✅ Veriler başarıyla kaydedildi!")
                            else:
                                st.error("❌ Kayıt sırasında hata oluştu!")
                
                else:
                    st.warning(f"⚠️ BTag {btag_input} için veri bulunamadı.")
            
            else:
                st.error("❌ Excel dosyasında 'BTag' sütunu bulunamadı!")
                st.info("📝 Beklenen sütunlar: ID, Kullanıcı Adı, Müşteri Adı, Para Yatırma Sayısı, Yatırımlar, Para Çekme Sayısı, Para Çekme Miktarı, BTag")
        
        except Exception as e:
            st.error(f"❌ Dosya işlenirken hata oluştu: {str(e)}")
    
    elif not btag_input:
        st.info("🏷️ Lütfen BTag numarasını girin.")
    elif not uploaded_file:
        st.info("📁 Lütfen Excel dosyasını yükleyin.")

def show_member_management(member_manager):
    st.header("👥 Üye Yönetimi")
    
    # Üye ekleme
    with st.expander("➕ Yeni Üye Ekle"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            new_member_id = st.text_input("🆔 Üye ID")
        with col2:
            new_username = st.text_input("👤 Kullanıcı Adı")
        with col3:
            new_fullname = st.text_input("📝 İsim Soyisim")
        
        if st.button("➕ Üye Ekle"):
            if new_member_id and new_username and new_fullname:
                success = member_manager.add_member(new_member_id, new_username, new_fullname)
                if success:
                    st.success("✅ Üye başarıyla eklendi!")
                    st.rerun()
                else:
                    st.error("❌ Bu üye zaten mevcut!")
            else:
                st.warning("⚠️ Tüm alanları doldurun!")
    
    # Üye listesi
    st.subheader("📋 Üye Listesi")
    
    members = member_manager.get_all_members()
    if members:
        # Arama özelliği
        search_term = st.text_input("🔍 Üye Ara", placeholder="İsim, kullanıcı adı veya ID ile ara...")
        
        if search_term:
            filtered_members = [
                m for m in members 
                if search_term.lower() in m['full_name'].lower() 
                or search_term.lower() in m['username'].lower()
                or search_term in str(m['member_id'])
            ]
        else:
            filtered_members = members
        
        # Üye tablosu
        for i, member in enumerate(filtered_members):
            col1, col2, col3, col4, col5 = st.columns([2, 2, 3, 1, 1])
            
            with col1:
                st.write(f"🆔 {member['member_id']}")
            with col2:
                st.write(f"👤 {member['username']}")
            with col3:
                st.write(f"📝 {member['full_name']}")
            with col4:
                status = "✅ Aktif" if member.get('is_active', True) else "❌ Banlandı"
                st.write(status)
            with col5:
                # Ban/Unban butonu
                if member.get('is_active', True):
                    if st.button(f"🚫 Ban", key=f"ban_{member['member_id']}"):
                        member_manager.toggle_member_status(member['member_id'])
                        st.success(f"Üye {member['username']} banlandı!")
                        st.rerun()
                else:
                    if st.button(f"✅ Aktif", key=f"unban_{member['member_id']}"):
                        member_manager.toggle_member_status(member['member_id'])
                        st.success(f"Üye {member['username']} aktif edildi!")
                        st.rerun()
        
        st.info(f"📊 Toplam {len(filtered_members)} üye gösteriliyor (Toplam: {len(members)})")
    
    else:
        st.info("👥 Henüz üye bulunmuyor.")

def show_reports(report_generator, member_manager):
    st.header("📊 Raporlar")
    
    # Tarih seçimi
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "📅 Başlangıç Tarihi",
            value=datetime.now().replace(day=1)
        )
    with col2:
        end_date = st.date_input(
            "📅 Bitiş Tarihi",
            value=datetime.now()
        )
    
    if start_date <= end_date:
        # Dönemsel rapor oluştur
        report_data = report_generator.get_period_report(start_date, end_date)
        
        if report_data and len(report_data) > 0:
            # Özet bilgiler
            st.subheader("📈 Dönem Özeti")
            
            total_deposits = sum([r.get('total_deposits', 0) for r in report_data])
            total_withdrawals = sum([r.get('total_withdrawals', 0) for r in report_data])
            net_total = total_deposits - total_withdrawals
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("💰 Toplam Yatırım", f"{total_deposits:,.2f} TL")
            with col2:
                st.metric("💸 Toplam Çekim", f"{total_withdrawals:,.2f} TL")
            with col3:
                delta_color = "normal" if net_total >= 0 else "inverse"
                st.metric("💵 Net Toplam", f"{net_total:,.2f} TL", delta_color=delta_color)
            
            st.markdown("---")
            
            # Detaylı tablo
            st.subheader("📋 Detaylı Rapor")
            
            df_report = pd.DataFrame(report_data)
            df_report['Net Toplam'] = df_report['total_deposits'] - df_report['total_withdrawals']
            
            # Sadece ihtiyaç duyduğumuz sütunları seç ve Türkçe isimlendirme yap
            columns_to_show = {
                'member_id': 'Üye ID',
                'member_name': 'Üye Adı', 
                'username': 'Kullanıcı Adı',
                'deposit_count': 'Yat. Adedi',
                'total_deposits': 'Top. Yat. Miktarı',
                'withdrawal_count': 'Çek. Adedi', 
                'total_withdrawals': 'Top. Çek. Miktarı',
                'Net Toplam': 'Net Toplam'
            }
            
            # Sadece var olan sütunları kullan
            available_columns = [col for col in columns_to_show.keys() if col in df_report.columns]
            df_display = df_report[available_columns].copy()
            
            # Türkçe isimlendirme için sadece var olan sütunları kullan
            available_mapping = {k: v for k, v in columns_to_show.items() if k in available_columns}
            df_display.rename(columns=available_mapping, inplace=True)
            
            # Renk kodlaması
            def color_values(val):
                try:
                    if float(val) > 0:
                        return 'color: green'
                    elif float(val) < 0:
                        return 'color: red'
                    else:
                        return 'color: black'
                except:
                    return 'color: black'
            
            # Renk kodlaması
            try:
                if 'Net Toplam' in df_display.columns:
                    styled_df = df_display.style.map(color_values, subset=['Net Toplam'])
                else:
                    styled_df = df_display
            except:
                styled_df = df_display
            
            st.dataframe(styled_df, use_container_width=True)
            
            # Excel indirme
            if st.button("📥 Excel Olarak İndir"):
                # Excel buffer oluştur
                from io import BytesIO
                buffer = BytesIO()
                
                # DataFrame'i Excel formatına dönüştür
                df_display.to_excel(buffer, sheet_name='Rapor', index=False, engine='openpyxl')
                buffer.seek(0)
                
                st.download_button(
                    label="📥 Rapor.xlsx İndir",
                    data=buffer.getvalue(),
                    file_name=f"rapor_{start_date}_{end_date}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        
        else:
            st.info("📊 Seçilen tarih aralığında veri bulunamadı.")
    
    else:
        st.error("❌ Başlangıç tarihi bitiş tarihinden sonra olamaz!")

def show_statistics(report_generator, member_manager):
    st.header("📈 İstatistikler")
    
    # Ay seçimi
    col1, col2 = st.columns(2)
    with col1:
        selected_year = st.selectbox("📅 Yıl", options=[2024, 2025], index=1)
    with col2:
        months = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                 "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        selected_month_name = st.selectbox("📅 Ay", options=months, 
                                         index=datetime.now().month - 1)
        selected_month = months.index(selected_month_name) + 1
    
    month_key = f"{selected_year}-{selected_month:02d}"
    
    # Aylık istatistikler
    monthly_stats = report_generator.get_monthly_statistics(month_key)
    
    if monthly_stats:
        # Genel özet
        st.subheader(f"📊 {selected_month_name} {selected_year} - Genel Özet")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("👥 Aktif Üye", monthly_stats['active_members'])
        with col2:
            st.metric("💰 Yatırım Yapan", monthly_stats['members_with_deposits'])
        with col3:
            st.metric("💸 Çekim Yapan", monthly_stats['members_with_withdrawals'])
        with col4:
            st.metric("📈 İşlem Yapan", monthly_stats['members_with_transactions'])
        
        st.markdown("---")
        
        # Yatırım/Çekim dağılımı
        col1, col2 = st.columns(2)
        
        with col1:
            # Yatırım dağılımı pasta grafiği
            fig_deposits = px.pie(
                values=[monthly_stats['members_with_deposits'], 
                       monthly_stats['active_members'] - monthly_stats['members_with_deposits']],
                names=['Yatırım Yapan', 'Yatırım Yapmayan'],
                title="💰 Yatırım Dağılımı",
                color_discrete_sequence=['#00CC96', '#FFA15A']
            )
            st.plotly_chart(fig_deposits, use_container_width=True)
        
        with col2:
            # Çekim dağılımı pasta grafiği
            fig_withdrawals = px.pie(
                values=[monthly_stats['members_with_withdrawals'], 
                       monthly_stats['active_members'] - monthly_stats['members_with_withdrawals']],
                names=['Çekim Yapan', 'Çekim Yapmayan'],
                title="💸 Çekim Dağılımı",
                color_discrete_sequence=['#FF6692', '#AB63FA']
            )
            st.plotly_chart(fig_withdrawals, use_container_width=True)
        
        # En çok yatırım/çekim yapan üyeler
        top_members = report_generator.get_top_members(month_key)
        
        if top_members:
            st.subheader("🏆 En Aktif Üyeler")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("💰 **En Çok Yatırım Yapanlar**")
                top_deposits = sorted(top_members, key=lambda x: x.get('total_deposits', 0), reverse=True)[:5]
                for i, member in enumerate(top_deposits, 1):
                    st.write(f"{i}. {member['member_name']} - {member.get('total_deposits', 0):,.2f} TL")
            
            with col2:
                st.write("💸 **En Çok Çekim Yapanlar**")
                top_withdrawals = sorted(top_members, key=lambda x: x.get('total_withdrawals', 0), reverse=True)[:5]
                for i, member in enumerate(top_withdrawals, 1):
                    st.write(f"{i}. {member['member_name']} - {member.get('total_withdrawals', 0):,.2f} TL")
        
        # Günlük trend grafiği
        daily_trend = report_generator.get_daily_trend(month_key)
        
        if daily_trend:
            st.subheader("📈 Günlük Trend")
            
            df_trend = pd.DataFrame(daily_trend)
            df_trend['date'] = pd.to_datetime(df_trend['date'])
            
            fig_trend = go.Figure()
            
            fig_trend.add_trace(go.Scatter(
                x=df_trend['date'],
                y=df_trend['total_deposits'],
                mode='lines+markers',
                name='Yatırım',
                line=dict(color='green')
            ))
            
            fig_trend.add_trace(go.Scatter(
                x=df_trend['date'],
                y=df_trend['total_withdrawals'],
                mode='lines+markers',
                name='Çekim',
                line=dict(color='red')
            ))
            
            fig_trend.update_layout(
                title="Günlük Yatırım/Çekim Trendi",
                xaxis_title="Tarih",
                yaxis_title="Miktar (TL)",
                hovermode='x'
            )
            
            st.plotly_chart(fig_trend, use_container_width=True)
    
    else:
        st.info(f"📊 {selected_month_name} {selected_year} için veri bulunamadı.")

if __name__ == "__main__":
    main()
