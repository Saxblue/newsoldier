import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

class Visualization:
    """Veri görselleştirme sınıfı"""
    
    def __init__(self):
        self.default_colors = px.colors.qualitative.Set3
    
    def create_daily_performance_chart(self, daily_data):
        """Günlük performans grafiği oluştur"""
        try:
            # Veriyi DataFrame'e çevir
            chart_data = []
            
            for date_str, btags in daily_data.items():
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                for btag, members in btags.items():
                    total_deposits = sum(m.get('total_deposits', 0) for m in members)
                    total_withdrawals = sum(m.get('total_withdrawals', 0) for m in members)
                    member_count = len(members)
                    deposit_count = sum(m.get('deposit_count', 0) for m in members)
                    
                    chart_data.append({
                        'date': date_obj,
                        'btag': btag,
                        'total_deposits': total_deposits,
                        'total_withdrawals': total_withdrawals,
                        'member_count': member_count,
                        'deposit_count': deposit_count,
                        'net_amount': total_deposits - total_withdrawals
                    })
            
            if not chart_data:
                return self.create_empty_chart("Veri bulunamadı")
            
            df = pd.DataFrame(chart_data)
            
            # Alt grafikler oluştur
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Günlük Yatırımlar', 'Günlük Çekimler', 'Üye Sayısı', 'Net Tutar'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Yatırımlar grafiği
            fig.add_trace(
                go.Scatter(
                    x=df['date'], 
                    y=df['total_deposits'],
                    mode='lines+markers',
                    name='Yatırımlar',
                    line=dict(color='green')
                ),
                row=1, col=1
            )
            
            # Çekimler grafiği
            fig.add_trace(
                go.Scatter(
                    x=df['date'], 
                    y=df['total_withdrawals'],
                    mode='lines+markers',
                    name='Çekimler',
                    line=dict(color='red')
                ),
                row=1, col=2
            )
            
            # Üye sayısı grafiği
            fig.add_trace(
                go.Scatter(
                    x=df['date'], 
                    y=df['member_count'],
                    mode='lines+markers',
                    name='Üye Sayısı',
                    line=dict(color='blue')
                ),
                row=2, col=1
            )
            
            # Net tutar grafiği
            fig.add_trace(
                go.Scatter(
                    x=df['date'], 
                    y=df['net_amount'],
                    mode='lines+markers',
                    name='Net Tutar',
                    line=dict(color='purple')
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=600,
                title_text="Günlük Performans Analizi",
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Grafik oluşturma hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_member_distribution_charts(self, members):
        """Üye dağılım grafikleri oluştur"""
        try:
            if not members:
                return self.create_empty_chart("Üye verisi bulunamadı")
            
            # Alt grafikler oluştur
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Durum Dağılımı', 'Son Yatırım Analizi', 'Bakiye Dağılımı', 'Günlere Göre Dağılım'),
                specs=[[{"type": "pie"}, {"type": "bar"}],
                       [{"type": "histogram"}, {"type": "bar"}]]
            )
            
            # 1. Durum dağılımı (Pie chart)
            status_counts = {}
            for member in members:
                status = 'Aktif' if member.get('is_active', True) else 'Pasif'
                status_counts[status] = status_counts.get(status, 0) + 1
            
            fig.add_trace(
                go.Pie(
                    labels=list(status_counts.keys()),
                    values=list(status_counts.values()),
                    name="Durum"
                ),
                row=1, col=1
            )
            
            # 2. Son yatırım analizi (Bar chart)
            deposit_ranges = {
                '0-7 gün': 0,
                '8-30 gün': 0,
                '31-90 gün': 0,
                '90+ gün': 0
            }
            
            for member in members:
                days = member.get('days_without_deposit', 999)
                if days <= 7:
                    deposit_ranges['0-7 gün'] += 1
                elif days <= 30:
                    deposit_ranges['8-30 gün'] += 1
                elif days <= 90:
                    deposit_ranges['31-90 gün'] += 1
                else:
                    deposit_ranges['90+ gün'] += 1
            
            fig.add_trace(
                go.Bar(
                    x=list(deposit_ranges.keys()),
                    y=list(deposit_ranges.values()),
                    name="Son Yatırım",
                    marker_color='lightblue'
                ),
                row=1, col=2
            )
            
            # 3. Bakiye dağılımı (Histogram)
            balances = [member.get('balance', 0) for member in members if member.get('balance', 0) > 0]
            
            if balances:
                fig.add_trace(
                    go.Histogram(
                        x=balances,
                        name="Bakiye",
                        marker_color='lightgreen'
                    ),
                    row=2, col=1
                )
            
            # 4. Günlere göre dağılım (Bar chart)
            day_ranges = {
                '0-7': 0, '8-14': 0, '15-30': 0, '31-60': 0, '60+': 0
            }
            
            for member in members:
                days = member.get('days_without_deposit', 999)
                if days <= 7:
                    day_ranges['0-7'] += 1
                elif days <= 14:
                    day_ranges['8-14'] += 1
                elif days <= 30:
                    day_ranges['15-30'] += 1
                elif days <= 60:
                    day_ranges['31-60'] += 1
                else:
                    day_ranges['60+'] += 1
            
            fig.add_trace(
                go.Bar(
                    x=list(day_ranges.keys()),
                    y=list(day_ranges.values()),
                    name="Gün Aralıkları",
                    marker_color='orange'
                ),
                row=2, col=2
            )
            
            fig.update_layout(
                height=600,
                title_text="Üye Dağılım Analizi",
                showlegend=False
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Üye dağılım grafiği hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_btag_comparison_chart(self, daily_data, btags=None):
        """BTag karşılaştırma grafiği"""
        try:
            if not daily_data:
                return self.create_empty_chart("Karşılaştırma verisi bulunamadı")
            
            comparison_data = []
            
            for date_str, btag_data in daily_data.items():
                for btag, members in btag_data.items():
                    if btags and btag not in btags:
                        continue
                    
                    total_deposits = sum(m.get('total_deposits', 0) for m in members)
                    member_count = len(members)
                    
                    comparison_data.append({
                        'date': date_str,
                        'btag': btag,
                        'total_deposits': total_deposits,
                        'member_count': member_count
                    })
            
            if not comparison_data:
                return self.create_empty_chart("Karşılaştırma verisi bulunamadı")
            
            df = pd.DataFrame(comparison_data)
            
            # BTag'lere göre renk ataması
            unique_btags = df['btag'].unique()
            colors = self.default_colors[:len(unique_btags)]
            
            fig = go.Figure()
            
            for i, btag in enumerate(unique_btags):
                btag_data = df[df['btag'] == btag]
                
                fig.add_trace(
                    go.Scatter(
                        x=btag_data['date'],
                        y=btag_data['total_deposits'],
                        mode='lines+markers',
                        name=f'BTag {btag}',
                        line=dict(color=colors[i % len(colors)])
                    )
                )
            
            fig.update_layout(
                title='BTag Karşılaştırma - Günlük Yatırımlar',
                xaxis_title='Tarih',
                yaxis_title='Toplam Yatırım (TRY)',
                height=400
            )
            
            return fig
            
        except Exception as e:
            st.error(f"BTag karşılaştırma grafiği hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_top_members_chart(self, members, metric='total_deposits', top_n=10):
        """En iyi üyeler grafiği"""
        try:
            if not members:
                return self.create_empty_chart("Üye verisi bulunamadı")
            
            # Metrik değerlerine göre sırala
            sorted_members = sorted(
                members, 
                key=lambda x: x.get(metric, 0), 
                reverse=True
            )[:top_n]
            
            names = [m.get('username', 'N/A') for m in sorted_members]
            values = [m.get(metric, 0) for m in sorted_members]
            
            metric_labels = {
                'total_deposits': 'Toplam Yatırım (TRY)',
                'balance': 'Bakiye (TRY)',
                'deposit_count': 'Yatırım Sayısı',
                'days_without_deposit': 'Yatırımsız Gün Sayısı'
            }
            
            title = f"En İyi {top_n} Üye - {metric_labels.get(metric, metric)}"
            
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=names,
                        y=values,
                        marker_color='lightblue'
                    )
                ]
            )
            
            fig.update_layout(
                title=title,
                xaxis_title='Üyeler',
                yaxis_title=metric_labels.get(metric, metric),
                height=400,
                xaxis_tickangle=-45
            )
            
            return fig
            
        except Exception as e:
            st.error(f"En iyi üyeler grafiği hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_trend_chart(self, data, date_column, value_column, title="Trend Analizi"):
        """Trend grafiği oluştur"""
        try:
            if not data:
                return self.create_empty_chart("Trend verisi bulunamadı")
            
            df = pd.DataFrame(data)
            
            if date_column not in df.columns or value_column not in df.columns:
                return self.create_empty_chart("Gerekli sütunlar bulunamadı")
            
            # Tarihe göre sırala
            df = df.sort_values(date_column)
            
            fig = go.Figure()
            
            # Ana trend çizgisi
            fig.add_trace(
                go.Scatter(
                    x=df[date_column],
                    y=df[value_column],
                    mode='lines+markers',
                    name='Trend',
                    line=dict(color='blue', width=2)
                )
            )
            
            # Trend çizgisi (linear regression)
            if len(df) > 1:
                from scipy import stats
                x_numeric = pd.to_numeric(pd.to_datetime(df[date_column]))
                slope, intercept, r_value, p_value, std_err = stats.linregress(x_numeric, df[value_column])
                
                trend_line = slope * x_numeric + intercept
                
                fig.add_trace(
                    go.Scatter(
                        x=df[date_column],
                        y=trend_line,
                        mode='lines',
                        name=f'Trend Çizgisi (R²={r_value**2:.3f})',
                        line=dict(color='red', dash='dash')
                    )
                )
            
            fig.update_layout(
                title=title,
                xaxis_title='Tarih',
                yaxis_title=value_column,
                height=400
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Trend grafiği hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_heatmap(self, data, x_column, y_column, value_column, title="Isı Haritası"):
        """Isı haritası oluştur"""
        try:
            if not data:
                return self.create_empty_chart("Isı haritası verisi bulunamadı")
            
            df = pd.DataFrame(data)
            
            required_columns = [x_column, y_column, value_column]
            if not all(col in df.columns for col in required_columns):
                return self.create_empty_chart("Gerekli sütunlar bulunamadı")
            
            # Pivot table oluştur
            pivot_df = df.pivot_table(
                index=y_column,
                columns=x_column,
                values=value_column,
                aggfunc='sum',
                fill_value=0
            )
            
            fig = go.Figure(
                data=go.Heatmap(
                    z=pivot_df.values,
                    x=pivot_df.columns,
                    y=pivot_df.index,
                    colorscale='Viridis',
                    showscale=True
                )
            )
            
            fig.update_layout(
                title=title,
                xaxis_title=x_column,
                yaxis_title=y_column,
                height=400
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Isı haritası hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_gauge_chart(self, value, max_value, title="Gösterge", unit=""):
        """Gösterge grafiği oluştur"""
        try:
            fig = go.Figure(
                go.Indicator(
                    mode = "gauge+number+delta",
                    value = value,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    title = {'text': title},
                    delta = {'reference': max_value * 0.8},
                    gauge = {
                        'axis': {'range': [None, max_value]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, max_value * 0.5], 'color': "lightgray"},
                            {'range': [max_value * 0.5, max_value * 0.8], 'color': "gray"}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': max_value * 0.9
                        }
                    }
                )
            )
            
            fig.update_layout(height=300)
            
            return fig
            
        except Exception as e:
            st.error(f"Gösterge grafiği hatası: {str(e)}")
            return self.create_empty_chart("Grafik oluşturulamadı")
    
    def create_empty_chart(self, message="Veri bulunamadı"):
        """Boş grafik oluştur"""
        fig = go.Figure()
        
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            xanchor='center', yanchor='middle',
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        
        fig.update_layout(
            height=400,
            xaxis={'visible': False},
            yaxis={'visible': False}
        )
        
        return fig
    
    def create_summary_metrics(self, data):
        """Özet metrikler oluştur"""
        try:
            if not data:
                return []
            
            metrics = []
            
            # Temel metrikler
            if 'total_deposits' in data:
                metrics.append({
                    'title': 'Toplam Yatırım',
                    'value': f"{data['total_deposits']:,.0f}",
                    'unit': 'TRY',
                    'color': 'green'
                })
            
            if 'total_withdrawals' in data:
                metrics.append({
                    'title': 'Toplam Çekim',
                    'value': f"{data['total_withdrawals']:,.0f}",
                    'unit': 'TRY',
                    'color': 'red'
                })
            
            if 'total_members' in data:
                metrics.append({
                    'title': 'Toplam Üye',
                    'value': f"{data['total_members']:,}",
                    'unit': '',
                    'color': 'blue'
                })
            
            if 'active_members' in data:
                metrics.append({
                    'title': 'Aktif Üye',
                    'value': f"{data['active_members']:,}",
                    'unit': '',
                    'color': 'orange'
                })
            
            return metrics
            
        except Exception as e:
            st.error(f"Özet metrik hatası: {str(e)}")
            return []
