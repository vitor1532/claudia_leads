import asyncio
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from playwright.async_api import async_playwright
import pandas as pd

class Claudia:
    def __init__(self, root):
        self.root = root
        self.root.title("Prospecção Ativa de Leads - Web Design (Google Maps)")
        self.root.geometry("620x580")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use("clam")

        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        lbl_title = ttk.Label(
            frame, 
            text="Capturador Avançado de Leads Locais", 
            font=("Helvetica", 16, "bold")
        )
        lbl_title.pack(pady=(0, 15))

        # Input Palavras-chave
        ttk.Label(
            frame, 
            text="Palavras-chave (separadas por vírgula):", 
            font=("Helvetica", 10, "bold")
        ).pack(anchor=tk.W)
        
        self.txt_keywords = ttk.Entry(frame, width=65)
        self.txt_keywords.pack(pady=(4, 12))
        self.txt_keywords.insert(0, "tatuador, psicologo, clinica odontologica")

        # Input Localizações
        ttk.Label(
            frame, 
            text="Cidades / Regiões (separadas por vírgula):", 
            font=("Helvetica", 10, "bold")
        ).pack(anchor=tk.W)
        
        self.txt_locations = ttk.Entry(frame, width=65)
        self.txt_locations.pack(pady=(4, 12))
        self.txt_locations.insert(0, "Juiz de Fora MG, São Paulo SP")

        # Frame de Opções
        opts_frame = ttk.Frame(frame)
        opts_frame.pack(fill=tk.X, pady=(0, 12))

        # Limite
        sub_frame_limit = ttk.Frame(opts_frame)
        sub_frame_limit.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

        ttk.Label(
            sub_frame_limit, 
            text="Limite por Busca:", 
            font=("Helvetica", 10, "bold")
        ).pack(anchor=tk.W)
        
        self.spin_limit = ttk.Spinbox(sub_frame_limit, from_=5, to=200, width=12)
        self.spin_limit.pack(anchor=tk.W, pady=(4, 0))
        self.spin_limit.set(20)

        # Nome do Arquivo CSV
        sub_frame_file = ttk.Frame(opts_frame)
        sub_frame_file.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Label(
            sub_frame_file, 
            text="Nome do Arquivo CSV:", 
            font=("Helvetica", 10, "bold")
        ).pack(anchor=tk.W)
        
        self.txt_filename = ttk.Entry(sub_frame_file, width=35)
        self.txt_filename.pack(anchor=tk.W, pady=(4, 0))
        self.txt_filename.insert(0, "leads_prospeccao_webdesign")

        # Botão
        self.btn_start = ttk.Button(
            frame, 
            text="Iniciar Captura de Leads", 
            command=self.start_scraping_thread
        )
        self.btn_start.pack(pady=10, fill=tk.X)

        # Console
        ttk.Label(frame, text="Status da Execução:", font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        self.txt_status = tk.Text(frame, height=9, width=70, state=tk.DISABLED, bg="#f5f5f5")
        self.txt_status.pack(pady=(4, 0))

    def log(self, message):
        self.txt_status.config(state=tk.NORMAL)
        self.txt_status.insert(tk.END, message + "\n")
        self.txt_status.see(tk.END)
        self.txt_status.config(state=tk.DISABLED)

    def start_scraping_thread(self):
        keywords = [k.strip() for k in self.txt_keywords.get().split(",") if k.strip()]
        locations = [l.strip() for l in self.txt_locations.get().split(",") if l.strip()]
        filename_input = self.txt_filename.get().strip()

        try:
            limit = int(self.spin_limit.get())
        except ValueError:
            messagebox.showwarning("Campo Inválido", "Informe um número válido para o limite.")
            return

        if not keywords or not locations or not filename_input:
            messagebox.showwarning("Campos Vazios", "Preencha todos os campos obrigatórios.")
            return

        filename = filename_input if filename_input.lower().endswith(".csv") else f"{filename_input}.csv"

        self.btn_start.config(state=tk.DISABLED)
        self.log("--- Iniciando processo de extração ---")

        thread = threading.Thread(
            target=self.run_async_scraper, 
            args=(keywords, locations, limit, filename), 
            daemon=True
        )
        thread.start()

    def run_async_scraper(self, keywords, locations, limit, filename):
        asyncio.run(self.scrape_leads(keywords, locations, limit, filename))

    async def scrape_leads(self, keywords, locations, limit, filename):
        all_leads = []

        async with async_playwright() as p:
            # headless=True executa sem abrir a janela. Mude para False se quiser ver navegando.
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(locale="pt-BR")
            page = await context.new_page()

            for location in locations:
                for keyword in keywords:
                    search_query = f"{keyword} em {location}"
                    self.log(f"\n[Buscando] '{search_query}'...")

                    try:
                        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(3000)

                        feed_selector = 'div[role="feed"]'
                        
                        # Tenta aguardar a presença do painel lateral de resultados
                        try:
                            await page.wait_for_selector(feed_selector, timeout=8000)
                        except Exception:
                            self.log("  -> Nenhum resultado retornado para essa combinação.")
                            continue

                        # Rola dinamicamente até obter o número desejado de itens
                        seen_titles = set()
                        scroll_attempts = 0
                        max_scrolls = limit * 2

                        while len(seen_titles) < limit and scroll_attempts < max_scrolls:
                            items = await page.query_selector_all('div[role="article"], div.Nv2PK')
                            
                            for item in items:
                                try:
                                    # Pega o título/nome do estabelecimento
                                    title_el = await item.query_selector('div.qBF1Pd, font')
                                    if not title_el:
                                        title_el = await item.query_selector('[aria-label]')
                                    
                                    if title_el:
                                        title_text = await title_el.text_content()
                                        if not title_text:
                                            title_text = await title_el.get_attribute('aria-label')

                                        if title_text and title_text not in seen_titles:
                                            seen_titles.add(title_text)
                                            
                                            # Extrai o link de detalhes
                                            link_el = await item.query_selector('a')
                                            link = await link_el.get_attribute('href') if link_el else ""

                                            all_leads.append({
                                                'Nome': title_text.strip(),
                                                'Categoria': keyword,
                                                'Cidade_Região': location,
                                                'Link_Maps': link,
                                                'Status_Inicial': 'Pendente Qualificação'
                                            })

                                            if len(seen_titles) >= limit:
                                                break
                                except Exception:
                                    continue

                            # Rola a barra lateral para carregar mais resultados
                            await page.eval_on_selector(
                                feed_selector, 
                                'el => el.scrollBy(0, 1500)'
                            )
                            await page.wait_for_timeout(1500)
                            scroll_attempts += 1

                        self.log(f"  -> Coletados {len(seen_titles)} leads para '{search_query}'")

                    except Exception as e:
                        self.log(f"  -> Erro ao processar '{search_query}': {str(e)}")

            await browser.close()

        if all_leads:
            df = pd.DataFrame(all_leads)
            # Remove duplicados com base no Nome
            df.drop_duplicates(subset=['Nome'], inplace=True)
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            
            caminho = os.path.abspath(filename)
            self.log(f"\n[FINALIZADO] Total final: {len(df)} leads salvos.")
            messagebox.showinfo("Sucesso", f"Processo concluído!\n\nSalvo em:\n{caminho}")
        else:
            self.log("\n[AVISO] Nenhum lead encontrado.")

        self.btn_start.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = Claudia(root)
    root.mainloop()