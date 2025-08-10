import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from io import BytesIO
import time

# Import custom modules
from github_manager import GitHubManager
from token_manager import TokenManager
from data_processor import DataProcessor
from member_manager import MemberManager
from visualization import Visualization
from utils import Utils

# Streamlit sayfa konfigürasyonu
st.set_page_config(
    page_title="BTag Affiliate Takip Sistemi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS stil eklemeleri
st.markdown("""
<style>
.success-box {
    padding: 10px;
    border-radius: 5px;
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    color: #155724;
    margin: 10px 0;
}
.error-box {
    padding: 10px;
    border-radius: 5px;
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    color: #721c24;
    margin: 10px 0;
}
.info-box {
    padding: 10px;
    border-radius: 5px;
    background-color: #d1ecf1;
    border: 1px solid #b8daff;
    color: #0c5460;
    margin: 10px 0;
}
</style>
""", unsafe_allow_html=True)

class BTagAffiliateSystem:
    def __init__(self):
        self.token_manager = TokenManager()
        self.github_manager = GitHubManager()
        self.data_processor = DataProcessor(self.github_manager)
        self.member_manager = MemberManager(self.token_manager, self.github_manager)
        self.visualization = Visualization()
        self.utils = Utils()
        
        # Initialize tokens
        self.initialize_tokens()
        
        # GitHub bağlantısını başlat
        self.initialize_github_connection()
        
        # Session state initialization
        if 'last_sync' not in st.session_state:
            st.session_state.last_sync = None
        if 'auto_sync_enabled' not in st.session_state:
            st.session_state.auto_sync_enabled = True
        if 'github_connected' not in st.session_state:
            st.session_state.github_connected = False
    
    def initialize_tokens(self):
        """Token'ları başlat - kullanıcı tarafından sağlanan token'ları kullan"""
        try:
            # Kullanıcının sağladığı güncel token'ları kullan
            api_token = "8d7974f38c6fae4e66f41dcf6805e648a9fa59c6682788e7fe61a4c8ea5e21e3"
            github_token = "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"
            
            # Token'ları kaydet
            self.token_manager.save_api_token(api_token)
            self.token_manager.save_github_token(github_token)
            
            # Environment variable'lara da set et
            os.environ["API_TOKEN"] = api_token
            os.environ["GITHUB_TOKEN"] = github_token
            
        except Exception as e:
            st.warning(f"Token başlatma hatası: {str(e)}")
    
    def initialize_github_connection(self):
        """GitHub bağlantısını başlat"""
        try:
            github_token = self.token_manager.get_github_token()
            if github_token:
                success = self.github_manager.set_token(github_token)
                if success:
                    st.session_state.github_connected = True
                    # Repository ayarla - varsayılan repo adını kullan
                    repo_name = os.getenv("GITHUB_REPO", "btag-affiliate-system")
                    self.github_manager.set_repo(repo_name)
                else:
                    st.session_state.github_connected = False
        except Exception as e:
            st.warning(f"GitHub bağlantısı başlatılamadı: {str(e)}")
    
    def show_header(self):
        """Ana başlık ve durum bilgisi"""
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            st.title("🎯 BTag Affiliate Takip Sistemi")
            st.markdown("*GitHub Entegrasyonlu Veri Yönetimi ve Analiz Platformu*")
        
        with col2:
            # GitHub bağlantı durumu
            if self.github_manager.is_connected():
                st.success("✅ GitHub Bağlı")
                st.session_state.github_connected = True
            else:
                st.error("❌ GitHub Bağlantısız")
                st.session_state.github_connected = False
        
        with col3:
            # Son senkronizasyon
            if st.session_state.last_sync:
                st.info(f"Son Sync: {st.session_state.last_sync.strftime('%H:%M')}")
            else:
                st.warning("Sync Bekleniyor")
    
    def show_sidebar(self):
        """Yan panel menüsü"""
        st.sidebar.title("📊 Kontrol Paneli")
        
        # GitHub durumu
        if st.session_state.github_connected:
            st.sidebar.success("🔗 GitHub Aktif")
        else:
            st.sidebar.error("🔗 GitHub Bağlantısız")
            if st.sidebar.button("🔧 GitHub Ayarla"):
                st.session_state.goto_settings = True
                st.rerun()
        
        # Menü seçimi
        menu_options = [
            "🏠 Ana Sayfa",
            "📁 Veri Yükleme",
            "👥 Üye Yönetimi", 
            "📈 Analiz & Raporlar",
            "🔧 Ayarlar",
            "🔄 GitHub Sync"
        ]
        
        selected_menu = st.sidebar.selectbox("Menü Seçin", menu_options)
        
        # Otomatik senkronizasyon ayarı
        st.sidebar.markdown("---")
        st.session_state.auto_sync_enabled = st.sidebar.checkbox(
            "🔄 Otomatik GitHub Sync", 
            value=st.session_state.auto_sync_enabled,
            help="Veri kaydedildiğinde otomatik olarak GitHub'a sync et"
        )
        
        # Hızlı sync butonu
        if st.session_state.github_connected:
            if st.sidebar.button("⚡ Hızlı Sync", use_container_width=True):
                self.sync_to_github()
        
        # Hızlı istatistikler
        self.show_quick_stats()
        
        return selected_menu
    
    def show_quick_stats(self):
        """Hızlı istatistikler"""
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Hızlı İstatistikler")
        
        try:
            # Toplam üye sayısı
            members = self.member_manager.get_all_members()
            total_members = len(members)
            active_members = len([m for m in members if m.get('is_active', True)])
            
            st.sidebar.metric("Toplam Üye", total_members)
            st.sidebar.metric("Aktif Üye", active_members)
            
            # Son 7 günde yatırım yapan üyeler
            recent_deposits = len([m for m in members if m.get('days_without_deposit', 999) <= 7])
            st.sidebar.metric("Son 7 Gün Aktif", recent_deposits)
            
            # Günlük veri sayısı
            daily_data = self.data_processor.load_daily_data()
            data_days = len(daily_data)
            st.sidebar.metric("Veri Günü", data_days)
            
        except Exception as e:
            st.sidebar.error(f"İstatistik hatası: {str(e)}")
    
    def show_home_page(self):
        """Ana sayfa"""
        st.header("📊 Dashboard")
        
        # Sistem durumu kartları
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            github_status = "🟢 Bağlı" if self.github_manager.is_connected() else "🔴 Bağlantısız"
            st.metric("GitHub Durumu", github_status)
        
        with col2:
            token_status = "🟢 Aktif" if self.token_manager.get_api_token() else "🔴 Eksik"
            st.metric("API Token", token_status)
        
        with col3:
            members_count = len(self.member_manager.get_all_members())
            st.metric("Toplam Üye", members_count)
        
        with col4:
            data_files = self.data_processor.get_data_file_count()
            st.metric("Veri Dosyaları", data_files)
        
        # GitHub bağlantı durumu kontrolü
        if not st.session_state.github_connected:
            st.warning("""
            ⚠️ **GitHub Bağlantısı Kontrol Ediliyor...** 
            
            GitHub bağlantısı kuruluyor. Lütfen bir kaç saniye bekleyin veya ayarlar sayfasından GitHub token'ınızı kontrol edin.
            """)
            
            # GitHub bağlantısını yeniden dene
            if st.button("🔄 GitHub Bağlantısını Yenile"):
                self.initialize_github_connection()
                st.rerun()
        
        # Son aktiviteler
        st.subheader("📝 Son Aktiviteler")
        self.show_recent_activities()
        
        # Hızlı görevler
        st.subheader("⚡ Hızlı Görevler")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Tüm Verileri Sync Et", use_container_width=True):
                if st.session_state.github_connected:
                    self.sync_all_data()
                else:
                    st.error("❌ GitHub bağlantısı gerekli!")
        
        with col2:
            if st.button("👥 Yeni Üyeler Ekle", use_container_width=True):
                st.session_state.goto_members = True
                st.rerun()
        
        with col3:
            if st.button("📊 Analiz Raporu", use_container_width=True):
                st.session_state.goto_analysis = True
                st.rerun()
    
    def show_data_upload_page(self):
        """Veri yükleme sayfası"""
        st.header("📁 Veri Yükleme ve İşleme")
        
        # BTag ID girişi
        btag_id = st.text_input("BTag ID", placeholder="Örn: 2424878")
        
        # Tarih seçimi
        selected_date = st.date_input("Veri Tarihi", datetime.now())
        
        # Excel dosya yükleme
        uploaded_file = st.file_uploader(
            "Excel Dosyası Seçin", 
            type=['xlsx', 'xls'],
            help="Üye verilerini içeren Excel dosyasını yükleyin"
        )
        
        if uploaded_file and btag_id:
            try:
                # Excel dosyasını oku
                df = pd.read_excel(uploaded_file)
                st.success(f"✅ Dosya başarıyla okundu. {len(df)} satır veri bulundu.")
                
                # Veri önizlemesi
                st.subheader("📋 Veri Önizlemesi")
                st.dataframe(df.head(10))
                
                # Veri işleme ve kaydetme
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("💾 Veriyi Kaydet", use_container_width=True):
                        self.process_and_save_data(df, btag_id, selected_date)
                
                with col2:
                    if st.button("🔄 Kaydet ve GitHub'a Sync Et", use_container_width=True):
                        success = self.process_and_save_data(df, btag_id, selected_date)
                        if success and st.session_state.github_connected:
                            self.sync_to_github()
                        elif success and not st.session_state.github_connected:
                            st.warning("⚠️ Veri kaydedildi ancak GitHub bağlantısı yok!")
                            
            except Exception as e:
                st.error(f"❌ Dosya okuma hatası: {str(e)}")
    
    def process_and_save_data(self, df, btag_id, date):
        """Veriyi işle ve kaydet"""
        try:
            with st.spinner("Veri işleniyor..."):
                # Veriyi işle
                processed_df = self.data_processor.process_excel_data(df)
                
                if processed_df is None:
                    st.error("❌ Veri işleme başarısız!")
                    return False
                
                # Günlük veriye kaydet
                success = self.data_processor.save_daily_data(processed_df, btag_id, date)
                
                if success:
                    st.success("✅ Veri başarıyla kaydedildi!")
                    
                    # Otomatik sync aktifse ve GitHub bağlı ise
                    if st.session_state.auto_sync_enabled and st.session_state.github_connected:
                        self.sync_to_github()
                    elif st.session_state.auto_sync_enabled and not st.session_state.github_connected:
                        st.info("ℹ️ GitHub bağlantısı olmadığı için otomatik sync atlandı.")
                    
                    return True
                else:
                    st.error("❌ Veri kaydetme başarısız!")
                    return False
                    
        except Exception as e:
            st.error(f"❌ Veri işleme hatası: {str(e)}")
            return False
    
    def show_member_management_page(self):
        """Üye yönetimi sayfası"""
        st.header("👥 Üye Yönetimi")
        
        tab1, tab2, tab3, tab4 = st.tabs(["➕ Üye Ekle", "📋 Üye Listesi", "🔍 Üye Arama", "🔄 API Yenile"])
        
        with tab1:
            self.show_add_member_tab()
        
        with tab2:
            self.show_member_list_tab()
        
        with tab3:
            self.show_member_search_tab()
        
        with tab4:
            self.show_api_refresh_tab()
    
    def show_add_member_tab(self):
        """Üye ekleme sekmesi"""
        st.subheader("➕ Yeni Üye Ekleme")
        
        # API token kontrolü
        api_token = self.token_manager.get_api_token()
        if not api_token:
            st.warning("⚠️ API token bulunamadı. Ayarlar sayfasından token ekleyin.")
            return
        
        # Tek üye ekleme
        st.markdown("**Tek Üye Ekle**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            member_id = st.text_input("Üye ID")
        with col2:
            username = st.text_input("Kullanıcı Adı (opsiyonel)")
        with col3:
            full_name = st.text_input("Ad Soyad (opsiyonel)")
        
        if st.button("👤 Tek Üye Ekle") and member_id:
            # Eğer username veya full_name boşsa API'den çek
            if not username or not full_name:
                with st.spinner("API'den üye bilgileri çekiliyor..."):
                    api_data = self.member_manager.fetch_member_api_data(member_id)
                    if api_data:
                        username = username or api_data.get('username', f'User_{member_id}')
                        full_name = full_name or api_data.get('full_name', f'Member {member_id}')
            
            success = self.member_manager.add_member(member_id, username, full_name)
            if success:
                st.success("✅ Üye başarıyla eklendi!")
                if st.session_state.auto_sync_enabled and st.session_state.github_connected:
                    self.sync_to_github()
            else:
                st.error("❌ Üye ekleme başarısız!")
        
        st.markdown("---")
        
        # Toplu üye ekleme
        st.markdown("**Toplu Üye Ekleme**")
        member_ids_text = st.text_area(
            "Üye ID'leri (Her satıra bir ID)", 
            height=150,
            placeholder="304680034\n304283610\n304170689"
        )
        
        if st.button("👥 Toplu Üye Ekle") and member_ids_text:
            member_ids = [id.strip() for id in member_ids_text.split('\n') if id.strip()]
            
            if member_ids:
                with st.spinner("Üyeler ekleniyor..."):
                    added_count = self.member_manager.add_members_bulk(member_ids)
                    st.success(f"✅ {added_count} üye başarıyla eklendi!")
                    
                    if st.session_state.auto_sync_enabled and st.session_state.github_connected:
                        self.sync_to_github()
    
    def show_member_list_tab(self):
        """Üye listesi sekmesi"""
        members = self.member_manager.get_all_members()
        
        if not members:
            st.info("📝 Henüz üye bulunmamaktadır.")
            return
        
        # Filtreleme seçenekleri
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status_filter = st.selectbox("Durum Filtresi", ["Tümü", "Aktif", "Pasif"])
        
        with col2:
            days_filter = st.selectbox(
                "Son Yatırım", 
                ["Tümü", "Son 7 gün", "Son 30 gün", "30+ gün"]
            )
        
        with col3:
            sort_by = st.selectbox(
                "Sıralama", 
                ["Son eklenen", "İsim", "Son yatırım", "Bakiye"]
            )
        
        # Filtrelenmiş üye listesi
        filtered_members = self.filter_members(members, status_filter, days_filter)
        filtered_members = self.sort_members(filtered_members, sort_by)
        
        # Sayfa başına üye sayısı
        page_size = st.selectbox("Sayfa başına üye", [10, 25, 50, 100], index=1)
        
        # Sayfalama
        total_members = len(filtered_members)
        total_pages = (total_members + page_size - 1) // page_size
        
        if total_pages > 1:
            page = st.selectbox(f"Sayfa (Toplam {total_pages})", range(1, total_pages + 1))
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            page_members = filtered_members[start_idx:end_idx]
        else:
            page_members = filtered_members
        
        # Üye tablosu
        if page_members:
            df_members = pd.DataFrame(page_members)
            
            # Görüntülenecek kolonları seç
            display_columns = [
                'member_id', 'username', 'full_name', 
                'days_without_deposit', 'balance', 'last_deposit_date',
                'email', 'phone'
            ]
            
            available_columns = [col for col in display_columns if col in df_members.columns]
            
            if available_columns:
                st.dataframe(
                    df_members[available_columns],
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.dataframe(df_members, use_container_width=True, hide_index=True)
        
        # İstatistikler
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Toplam Üye", len(members))
        with col2:
            active_count = len([m for m in members if m.get('is_active', True)])
            st.metric("Aktif Üye", active_count)
        with col3:
            recent_deposits = len([m for m in members if m.get('days_without_deposit', 999) <= 7])
            st.metric("Son 7 Gün Aktif", recent_deposits)
        with col4:
            total_balance = sum(m.get('balance', 0) for m in members)
            st.metric("Toplam Bakiye", f"{total_balance:,.2f} TRY")
    
    def show_member_search_tab(self):
        """Üye arama sekmesi"""
        search_term = st.text_input("🔍 Üye Ara (ID, kullanıcı adı veya isim)")
        
        if search_term:
            members = self.member_manager.get_all_members()
            found_members = []
            
            for member in members:
                if (search_term.lower() in member.get('member_id', '').lower() or
                    search_term.lower() in member.get('username', '').lower() or
                    search_term.lower() in member.get('full_name', '').lower()):
                    found_members.append(member)
            
            if found_members:
                st.success(f"✅ {len(found_members)} üye bulundu.")
                
                for member in found_members:
                    with st.expander(f"👤 {member.get('username', 'N/A')} - {member.get('full_name', 'N/A')}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"**ID:** {member.get('member_id', 'N/A')}")
                            st.write(f"**Email:** {member.get('email', 'N/A')}")
                            st.write(f"**Telefon:** {member.get('phone', 'N/A')}")
                            st.write(f"**Durum:** {'Aktif' if member.get('is_active', True) else 'Pasif'}")
                        
                        with col2:
                            st.write(f"**Bakiye:** {member.get('balance', 0)} {member.get('currency', 'TRY')}")
                            st.write(f"**Son Yatırım:** {member.get('last_deposit_date', 'Bilinmiyor')}")
                            st.write(f"**Yatırımsız Gün:** {member.get('days_without_deposit', 'N/A')}")
                            st.write(f"**Kayıt Tarihi:** {member.get('registration_date', 'N/A')}")
                        
                        # Üye işlemleri
                        col3, col4 = st.columns(2)
                        with col3:
                            if st.button(f"🔄 API Yenile", key=f"refresh_{member['member_id']}"):
                                self.member_manager.fetch_member_api_data(member['member_id'])
                                st.success("API verileri yenilendi!")
                                st.rerun()
                        
                        with col4:
                            if member.get('is_active', True):
                                if st.button(f"⏸️ Pasif Yap", key=f"deactivate_{member['member_id']}"):
                                    self.member_manager.deactivate_member(member['member_id'])
                                    st.success("Üye pasif yapıldı!")
                                    st.rerun()
                            else:
                                if st.button(f"▶️ Aktif Yap", key=f"activate_{member['member_id']}"):
                                    self.member_manager.activate_member(member['member_id'])
                                    st.success("Üye aktif yapıldı!")
                                    st.rerun()
            else:
                st.warning("⚠️ Eşleşen üye bulunamadı.")
    
    def show_api_refresh_tab(self):
        """API yenileme sekmesi"""
        st.subheader("🔄 API Verilerini Yenile")
        
        api_token = self.token_manager.get_api_token()
        if not api_token:
            st.warning("⚠️ API token bulunamadı. Ayarlar sayfasından token ekleyin.")
            return
        
        st.info("Bu işlem tüm üyelerin API verilerini yeniler. İşlem uzun sürebilir.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Tüm Üyeleri Yenile", use_container_width=True):
                updated_count = self.member_manager.refresh_all_members_api_data()
                st.success(f"✅ {updated_count} üyenin verileri yenilendi!")
                
                if st.session_state.auto_sync_enabled and st.session_state.github_connected:
                    self.sync_to_github()
        
        with col2:
            if st.button("🧪 API Bağlantısını Test Et", use_container_width=True):
                if self.member_manager.test_api_connection():
                    st.success("✅ API bağlantısı başarılı!")
                else:
                    st.error("❌ API bağlantısı başarısız!")
    
    def show_analysis_page(self):
        """Analiz ve raporlar sayfası"""
        st.header("📈 Analiz & Raporlar")
        
        # Analiz türü seçimi
        analysis_type = st.selectbox(
            "Analiz Türü Seçin",
            ["Günlük Performans", "Üye Analizi", "BTag Karşılaştırma", "Trend Analizi"]
        )
        
        if analysis_type == "Günlük Performans":
            self.show_daily_performance_analysis()
        elif analysis_type == "Üye Analizi":
            self.show_member_analysis()
        elif analysis_type == "BTag Karşılaştırma":
            self.show_btag_comparison_analysis()
        elif analysis_type == "Trend Analizi":
            self.show_trend_analysis()
    
    def show_daily_performance_analysis(self):
        """Günlük performans analizi"""
        st.subheader("📊 Günlük Performans Analizi")
        
        # Tarih aralığı seçimi
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Başlangıç Tarihi", datetime.now() - timedelta(days=30))
        with col2:
            end_date = st.date_input("Bitiş Tarihi", datetime.now())
        
        # Analiz verilerini çek
        daily_data = self.data_processor.get_daily_data_range(start_date, end_date)
        
        if daily_data:
            # Görselleştirme
            fig = self.visualization.create_daily_performance_chart(daily_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Özet istatistikler
            stats = self.data_processor.get_summary_stats(start_date, end_date)
            if stats:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Toplam Üye", stats.get('total_members', 0))
                with col2:
                    st.metric("Toplam Yatırım", f"{stats.get('total_deposits', 0):,.0f} TRY")
                with col3:
                    st.metric("Toplam Çekim", f"{stats.get('total_withdrawals', 0):,.0f} TRY")
                with col4:
                    net_amount = stats.get('total_deposits', 0) - stats.get('total_withdrawals', 0)
                    st.metric("Net Tutar", f"{net_amount:,.0f} TRY")
        else:
            st.info("📝 Seçilen tarih aralığında veri bulunmamaktadır.")
    
    def show_member_analysis(self):
        """Üye analizi"""
        st.subheader("👥 Üye Analizi")
        
        members = self.member_manager.get_all_members()
        
        if members:
            # Üye dağılım grafikleri
            fig = self.visualization.create_member_distribution_charts(members)
            st.plotly_chart(fig, use_container_width=True)
            
            # En iyi üyeler
            st.subheader("🏆 En İyi Üyeler")
            metric_choice = st.selectbox("Metrik Seçin", ["balance", "total_deposits", "days_without_deposit"])
            
            top_fig = self.visualization.create_top_members_chart(members, metric_choice, 10)
            st.plotly_chart(top_fig, use_container_width=True)
            
            # Risk analizi
            st.subheader("⚠️ Risk Analizi")
            risk_members = [m for m in members if m.get('days_without_deposit', 999) > 30]
            high_risk_members = [m for m in members if m.get('days_without_deposit', 999) > 90]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Riskli Üye (30+ gün)", len(risk_members))
            with col2:
                st.metric("Yüksek Risk (90+ gün)", len(high_risk_members))
            with col3:
                risk_percentage = (len(risk_members) / len(members) * 100) if members else 0
                st.metric("Risk Oranı", f"{risk_percentage:.1f}%")
        else:
            st.info("📝 Analiz için üye verisi bulunmamaktadır.")
    
    def show_btag_comparison_analysis(self):
        """BTag karşılaştırma analizi"""
        st.subheader("🔄 BTag Karşılaştırma")
        
        daily_data = self.data_processor.load_daily_data()
        
        if daily_data:
            # Mevcut BTag'leri al
            all_btags = set()
            for date_data in daily_data.values():
                all_btags.update(date_data.keys())
            
            if all_btags:
                selected_btags = st.multiselect("Karşılaştırılacak BTag'leri seçin", list(all_btags))
                
                if selected_btags:
                    fig = self.visualization.create_btag_comparison_chart(daily_data, selected_btags)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("Karşılaştırma için BTag seçin.")
            else:
                st.info("BTag verisi bulunamadı.")
        else:
            st.info("Karşılaştırma için veri bulunamadı.")
    
    def show_trend_analysis(self):
        """Trend analizi"""
        st.subheader("📈 Trend Analizi")
        st.info("🚧 Trend analizi geliştirme aşamasında...")
    
    def show_settings_page(self):
        """Ayarlar sayfası"""
        st.header("🔧 Sistem Ayarları")
        
        tab1, tab2, tab3 = st.tabs(["🔑 Token Ayarları", "🔄 GitHub Ayarları", "⚙️ Genel Ayarlar"])
        
        with tab1:
            self.show_token_settings()
        
        with tab2:
            self.show_github_settings()
        
        with tab3:
            self.show_general_settings()
    
    def show_token_settings(self):
        """Token ayarları"""
        st.subheader("🔑 API Token Ayarları")
        
        current_token = self.token_manager.get_api_token()
        
        # Mevcut token bilgilerini göster
        if current_token:
            st.success("✅ API Token aktif")
            masked_token = self.utils.mask_sensitive_info(current_token)
            st.code(f"Token: {masked_token}")
        
        # Token girişi
        new_token = st.text_input(
            "Yeni API Token", 
            placeholder="Yeni API token'ınızı buraya girin",
            type="password",
            help="BetConstruct API için gerekli token"
        )
        
        api_url = st.text_input(
            "API URL",
            value=self.token_manager.get_api_url(),
            help="API endpoint URL"
        )
        
        if st.button("💾 API Token Kaydet"):
            if new_token.strip():
                success = self.token_manager.save_api_token(new_token.strip(), api_url)
                if success:
                    st.success("✅ API Token başarıyla kaydedildi!")
                else:
                    st.error("❌ API Token kaydetme hatası!")
            else:
                st.warning("⚠️ Lütfen geçerli bir token girin!")
        
        # Token test etme
        if current_token:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧪 API Token Test Et"):
                    self.test_api_token()
            
            with col2:
                if st.button("👁️ Token Bilgilerini Göster"):
                    token_info = self.token_manager.get_token_info()
                    st.json(token_info)
    
    def show_github_settings(self):
        """GitHub ayarları"""
        st.subheader("🔄 GitHub Entegrasyon Ayarları")
        
        st.info("""
        **GitHub PAT Token Nasıl Alınır:**
        1. GitHub'da Settings > Developer settings > Personal access tokens > Tokens (classic) 
        2. "Generate new token (classic)" butonuna tıklayın
        3. "repo" izinlerini seçin
        4. Token'ı kopyalayın ve aşağıya yapıştırın
        """)
        
        current_github_token = self.token_manager.get_github_token()
        
        # Mevcut GitHub token durumu
        if current_github_token:
            st.success("✅ GitHub Token aktif")
            masked_token = self.utils.mask_sensitive_info(current_github_token)
            st.code(f"Token: {masked_token}")
        
        github_token = st.text_input(
            "GitHub Personal Access Token (PAT)",
            placeholder="GitHub PAT token'ınızı buraya girin",
            type="password",
            help="GitHub'a otomatik commit/push için gerekli"
        )
        
        repo_name = st.text_input(
            "Repository Adı",
            value=os.getenv("GITHUB_REPO", "btag-affiliate-system"),
            help="Örn: username/repo-name"
        )
        
        if st.button("💾 GitHub Ayarlarını Kaydet"):
            if github_token.strip():
                success = self.token_manager.save_github_token(github_token.strip())
                if success:
                    # GitHub Manager'ı yeniden başlat
                    self.github_manager.set_token(github_token.strip())
                    self.github_manager.set_repo(repo_name)
                    
                    # Bağlantıyı test et
                    if self.github_manager.test_connection():
                        st.session_state.github_connected = True
                        st.success("✅ GitHub ayarları kaydedildi ve bağlantı başarılı!")
                    else:
                        st.session_state.github_connected = False
                        st.error("❌ GitHub ayarları kaydedildi ancak bağlantı başarısız!")
                else:
                    st.error("❌ GitHub ayarları kaydetme hatası!")
            else:
                st.warning("⚠️ Lütfen geçerli bir GitHub token girin!")
        
        # GitHub bağlantı testi
        if current_github_token:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🧪 GitHub Bağlantısını Test Et"):
                    self.test_github_connection()
            
            with col2:
                if st.button("📊 Repository Bilgileri"):
                    if self.github_manager.is_connected():
                        repo_stats = self.github_manager.get_repo_stats()
                        if repo_stats:
                            st.json(repo_stats)
                        else:
                            st.error("Repository bilgileri alınamadı")
                    else:
                        st.error("GitHub bağlantısı yok")
    
    def show_general_settings(self):
        """Genel ayarlar"""
        st.subheader("⚙️ Genel Sistem Ayarları")
        
        # Otomatik sync ayarları
        auto_sync = st.checkbox(
            "🔄 Otomatik GitHub Senkronizasyonu",
            value=st.session_state.auto_sync_enabled,
            help="Veri kaydedildiğinde otomatik olarak GitHub'a sync et"
        )
        
        # Veri saklama ayarları
        data_retention = st.number_input(
            "Veri Saklama Süresi (gün)",
            min_value=30,
            max_value=365,
            value=90,
            help="Veriler kaç gün saklanacak"
        )
        
        # Veri temizleme
        if st.button("🧹 Eski Verileri Temizle"):
            cleaned = self.data_processor.clean_old_data(data_retention)
            if cleaned:
                st.success(f"✅ {data_retention} günden eski veriler temizlendi!")
            else:
                st.info("📝 Temizlenecek eski veri bulunamadı.")
        
        if st.button("💾 Genel Ayarları Kaydet"):
            st.session_state.auto_sync_enabled = auto_sync
            st.success("✅ Ayarlar kaydedildi!")
        
        # Veri bütünlük kontrolü
        st.markdown("---")
        st.subheader("🔍 Veri Bütünlük Kontrolü")
        
        if st.button("🔍 Veri Bütünlüğünü Kontrol Et"):
            issues = self.data_processor.validate_data_integrity()
            if issues:
                st.error(f"❌ {len(issues)} veri bütünlük sorunu bulundu:")
                for issue in issues[:10]:  # İlk 10 sorunu göster
                    st.write(f"• {issue}")
            else:
                st.success("✅ Veri bütünlüğü sorunsuz!")
    
    def show_github_sync_page(self):
        """GitHub senkronizasyon sayfası"""
        st.header("🔄 GitHub Senkronizasyon")
        
        # Senkronizasyon durumu
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if self.github_manager.is_connected():
                st.success("✅ GitHub Bağlı")
            else:
                st.error("❌ GitHub Bağlantısız")
        
        with col2:
            if st.session_state.last_sync:
                st.info(f"Son Sync: {st.session_state.last_sync.strftime('%H:%M:%S')}")
            else:
                st.warning("Henüz sync yapılmadı")
        
        with col3:
            pending_count = self.get_pending_changes_count()
            st.metric("Bekleyen Değişiklik", pending_count)
        
        # GitHub bağlantısı yoksa uyarı
        if not self.github_manager.is_connected():
            st.warning("""
            ⚠️ **GitHub Bağlantısı Yok!**
            
            Senkronizasyon yapmak için önce Ayarlar sayfasından GitHub PAT token'ınızı ekleyin.
            """)
            return
        
        # Senkronizasyon işlemleri
        st.subheader("🔄 Senkronizasyon İşlemleri")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Tüm Verileri GitHub'a Gönder", use_container_width=True):
                self.sync_all_data()
        
        with col2:
            if st.button("📥 GitHub'dan Verileri Çek", use_container_width=True):
                self.pull_from_github()
        
        # Backup işlemleri
        st.subheader("💾 Backup İşlemleri")
        
        col1, col2 = st.columns(2)
        
        with col1:
            backup_name = st.text_input("Backup Adı", value=f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}")
            if st.button("💾 Backup Oluştur", use_container_width=True):
                success = self.github_manager.create_backup(backup_name)
                if success:
                    st.success("✅ Backup başarıyla oluşturuldu!")
                else:
                    st.error("❌ Backup oluşturma başarısız!")
        
        with col2:
            backups = self.github_manager.list_backups()
            if backups:
                backup_choice = st.selectbox("Geri Yüklenecek Backup", [b['name'] for b in backups])
                if st.button("📥 Backup Geri Yükle", use_container_width=True):
                    success = self.github_manager.restore_backup(backup_choice)
                    if success:
                        st.success("✅ Backup başarıyla geri yüklendi!")
                        st.rerun()
                    else:
                        st.error("❌ Backup geri yükleme başarısız!")
        
        # Son sync logları
        st.subheader("📝 Senkronizasyon Geçmişi")
        self.show_sync_history()
    
    def sync_all_data(self):
        """Tüm verileri GitHub'a sync et"""
        try:
            if not self.github_manager.is_connected():
                st.error("❌ GitHub bağlantısı yok!")
                return
            
            with st.spinner("GitHub'a senkronize ediliyor..."):
                success = self.github_manager.sync_all_files()
                
                if success:
                    st.session_state.last_sync = datetime.now()
                    st.success("✅ Tüm veriler başarıyla GitHub'a gönderildi!")
                else:
                    st.error("❌ GitHub sync işlemi başarısız!")
                    
        except Exception as e:
            st.error(f"❌ Sync hatası: {str(e)}")
    
    def sync_to_github(self):
        """Verileri GitHub'a sync et"""
        if not self.github_manager.is_connected():
            st.warning("⚠️ GitHub bağlantısı yok, sync atlandı.")
            return
        
        try:
            with st.spinner("GitHub'a sync ediliyor..."):
                success = self.github_manager.sync_data_files()
                if success:
                    st.session_state.last_sync = datetime.now()
                    st.success("✅ Veriler GitHub'a sync edildi!")
                else:
                    st.error("❌ GitHub sync başarısız!")
        except Exception as e:
            st.error(f"❌ GitHub sync hatası: {str(e)}")
    
    def pull_from_github(self):
        """GitHub'dan verileri çek"""
        try:
            if not self.github_manager.is_connected():
                st.error("❌ GitHub bağlantısı yok!")
                return
            
            with st.spinner("GitHub'dan veriler çekiliyor..."):
                success = self.github_manager.pull_data_files()
                
                if success:
                    st.success("✅ Veriler GitHub'dan başarıyla çekildi!")
                    st.rerun()
                else:
                    st.error("❌ GitHub'dan veri çekme başarısız!")
                    
        except Exception as e:
            st.error(f"❌ Pull hatası: {str(e)}")
    
    def get_pending_changes_count(self):
        """Bekleyen değişiklik sayısını getir"""
        try:
            if not self.github_manager.is_connected():
                return 0
            return self.github_manager.get_pending_changes_count()
        except:
            return 0
    
    def show_sync_history(self):
        """Sync geçmişini göster"""
        try:
            history = self.github_manager.get_sync_history()
            if history:
                # Son 20 kaydı göster
                recent_history = history[-20:]
                df_history = pd.DataFrame(recent_history)
                
                # Zaman damgasını düzenle
                if 'timestamp' in df_history.columns:
                    df_history['timestamp'] = pd.to_datetime(df_history['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                st.dataframe(df_history, use_container_width=True, hide_index=True)
            else:
                st.info("📝 Henüz sync geçmişi bulunmamaktadır.")
        except Exception as e:
            st.error(f"Geçmiş yükleme hatası: {str(e)}")
    
    def show_recent_activities(self):
        """Son aktiviteleri göster"""
        activities = []
        
        # Son eklenen üyeler
        try:
            members = self.member_manager.get_all_members()
            recent_members = sorted(
                [m for m in members if m.get('created_at')],
                key=lambda x: x['created_at'],
                reverse=True
            )[:5]
            
            for member in recent_members:
                activities.append({
                    'time': member.get('created_at', ''),
                    'action': f"👤 Yeni üye eklendi: {member.get('username', 'N/A')}",
                    'type': 'member'
                })
        except:
            pass
        
        # Son sync işlemleri
        if st.session_state.last_sync:
            activities.append({
                'time': st.session_state.last_sync.isoformat(),
                'action': "🔄 GitHub sync yapıldı",
                'type': 'sync'
            })
        
        # Günlük veri girişleri
        try:
            daily_data = self.data_processor.load_daily_data()
            recent_dates = sorted(daily_data.keys(), reverse=True)[:3]
            
            for date_str in recent_dates:
                btag_count = len(daily_data[date_str])
                activities.append({
                    'time': f"{date_str}T12:00:00",
                    'action': f"📊 Günlük veri eklendi: {btag_count} BTag",
                    'type': 'data'
                })
        except:
            pass
        
        if activities:
            activities = sorted(activities, key=lambda x: x['time'], reverse=True)[:10]
            
            for activity in activities:
                try:
                    time_obj = datetime.fromisoformat(activity['time'].replace('Z', ''))
                    time_str = time_obj.strftime('%Y-%m-%d %H:%M')
                except:
                    time_str = activity['time']
                
                st.markdown(f"**{activity['action']}**")
                st.caption(f"⏰ {time_str}")
                st.markdown("---")
        else:
            st.info("📝 Henüz aktivite bulunmamaktadır.")
    
    def test_api_token(self):
        """API token test et"""
        try:
            with st.spinner("API token test ediliyor..."):
                success = self.member_manager.test_api_connection()
                
                if success:
                    st.success("✅ API token geçerli ve çalışıyor!")
                else:
                    st.error("❌ API token geçersiz veya API'ye erişim yok!")
                    
        except Exception as e:
            st.error(f"❌ API test hatası: {str(e)}")
    
    def test_github_connection(self):
        """GitHub bağlantısını test et"""
        try:
            with st.spinner("GitHub bağlantısı test ediliyor..."):
                success = self.github_manager.test_connection()
                
                if success:
                    st.session_state.github_connected = True
                    st.success("✅ GitHub bağlantısı başarılı!")
                else:
                    st.session_state.github_connected = False
                    st.error("❌ GitHub bağlantısı başarısız!")
                    
        except Exception as e:
            st.error(f"❌ GitHub test hatası: {str(e)}")
    
    def filter_members(self, members, status_filter, days_filter):
        """Üyeleri filtrele"""
        filtered = members.copy()
        
        # Durum filtresi
        if status_filter == "Aktif":
            filtered = [m for m in filtered if m.get('is_active', True)]
        elif status_filter == "Pasif":
            filtered = [m for m in filtered if not m.get('is_active', True)]
        
        # Gün filtresi
        if days_filter == "Son 7 gün":
            filtered = [m for m in filtered if m.get('days_without_deposit', 999) <= 7]
        elif days_filter == "Son 30 gün":
            filtered = [m for m in filtered if m.get('days_without_deposit', 999) <= 30]
        elif days_filter == "30+ gün":
            filtered = [m for m in filtered if m.get('days_without_deposit', 999) > 30]
        
        return filtered
    
    def sort_members(self, members, sort_by):
        """Üyeleri sırala"""
        if sort_by == "İsim":
            return sorted(members, key=lambda x: x.get('full_name', ''))
        elif sort_by == "Son yatırım":
            return sorted(members, key=lambda x: x.get('days_without_deposit', 999))
        elif sort_by == "Bakiye":
            return sorted(members, key=lambda x: x.get('balance', 0), reverse=True)
        else:  # Son eklenen
            return sorted(members, key=lambda x: x.get('created_at', ''), reverse=True)
    
    def run(self):
        """Ana uygulama çalıştır"""
        try:
            # Başlık göster
            self.show_header()
            
            # Yan panel menüsü
            selected_menu = self.show_sidebar()
            
            # Sayfa yönlendirmeleri
            if hasattr(st.session_state, 'goto_members') and st.session_state.goto_members:
                selected_menu = "👥 Üye Yönetimi"
                del st.session_state.goto_members
            
            if hasattr(st.session_state, 'goto_analysis') and st.session_state.goto_analysis:
                selected_menu = "📈 Analiz & Raporlar"
                del st.session_state.goto_analysis
            
            if hasattr(st.session_state, 'goto_settings') and st.session_state.goto_settings:
                selected_menu = "🔧 Ayarlar"
                del st.session_state.goto_settings
            
            # Seçilen sayfayı göster
            if selected_menu == "🏠 Ana Sayfa":
                self.show_home_page()
            elif selected_menu == "📁 Veri Yükleme":
                self.show_data_upload_page()
            elif selected_menu == "👥 Üye Yönetimi":
                self.show_member_management_page()
            elif selected_menu == "📈 Analiz & Raporlar":
                self.show_analysis_page()
            elif selected_menu == "🔧 Ayarlar":
                self.show_settings_page()
            elif selected_menu == "🔄 GitHub Sync":
                self.show_github_sync_page()
                
        except Exception as e:
            st.error(f"❌ Uygulama hatası: {str(e)}")
            st.exception(e)

# Ana uygulama
def main():
    """Ana fonksiyon"""
    try:
        app = BTagAffiliateSystem()
        app.run()
    except Exception as e:
        st.error(f"❌ Sistem başlatma hatası: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()
