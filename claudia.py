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
        self.root.title("Prospecção Ativa de Leads - Web Design")
        self.root.geometry("620x620")
        self.root.resizable(False, False)

        # Flag de controle de interrupção
        self.stop_requested = False

        # Estilo visual da interface
        style = ttk.Style()
        style.theme_use("clam")

        # Container Principal
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Título
        lbl_title = ttk.Label(
            frame, 
            text="Capturador de Leads Locais", 
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
        self.txt_locations.insert(0, "São Paulo SP, Juiz de Fora MG")

        # Frame Horizontal para Limite e Nome do Arquivo CSV
        opts_frame = ttk.Frame(frame)
        opts_frame.pack(fill=tk.X, pady=(0, 12))

        # Input Limite por busca
        sub_frame_limit = ttk.Frame(opts_frame)
        sub_frame_limit.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

        ttk.Label(
            sub_frame_limit, 
            text="Limite por Busca:", 
            font=("Helvetica", 10, "bold")
        ).pack(anchor=tk.W)
        
        self.spin_limit = ttk.Spinbox(sub_frame_limit, from_=5, to=100, width=12)
        self.spin_limit.pack(anchor=tk.W, pady=(4, 0))
        self.spin_limit.set(10)

        # Input Nome do Arquivo CSV
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

        # Container para Botões de Ação (Iniciar e Cancelar)
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10, fill=tk.X)

        self.btn_start = ttk.Button(
            btn_frame, 
            text="Iniciar Captura de Leads", 
            command=self.start_scraping_thread
        )
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.btn_stop = ttk.Button(
            btn_frame, 
            text="Cancelar Execução", 
            command=self.stop_scraping,
            state=tk.DISABLED
        )
        self.btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))

        # Console / Logs de Status
        ttk.Label(frame, text="Status da Execução:", font=("Helvetica", 9, "bold")).pack(anchor=tk.W)
        self.txt_status = tk.Text(frame, height=9, width=70, state=tk.DISABLED, bg="#f5f5f5")
        self.txt_status.pack(pady=(4, 0))

    def log(self, message):
        self.txt_status.config(state=tk.NORMAL)
        self.txt_status.insert(tk.END, message + "\n")
        self.txt_status.see(tk.END)
        self.txt_status.config(state=tk.DISABLED)

    def stop_scraping(self):
        """Solicita a interrupção do loop de raspagem."""
        if not self.stop_requested:
            self.stop_requested = True
            self.log("\n[SOLICITAÇÃO] Cancelando a operação... Aguarde o encerramento do ciclo.")
            self.btn_stop.config(state=tk.DISABLED)

    def start_scraping_thread(self):
        keywords = [k.strip() for k in self.txt_keywords.get().split(",") if k.strip()]
        locations = [l.strip() for l in self.txt_locations.get().split(",") if l.strip()]
        filename_input = self.txt_filename.get().strip()

        try:
            limit = int(self.spin_limit.get())
        except ValueError:
            messagebox.showwarning("Campo Inválido", "Informe um número válido para o limite.")
            return

        if not keywords or not locations:
            messagebox.showwarning("Campos Vazios", "Preencha as palavras-chave e as localizações.")
            return

        if not filename_input:
            messagebox.showwarning("Nome do Arquivo", "Informe um nome válido para salvar o arquivo CSV.")
            return

        # Ajusta a extensão caso a pessoa digite ou não com ".csv"
        if not filename_input.lower().endswith(".csv"):
            filename = f"{filename_input}.csv"
        else:
            filename = filename_input

        # Redefine a flag de parada e ajusta os botões
        self.stop_requested = False
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        
        self.log("--- Iniciando processo de extração ---")

        # Executa a raspagem em uma thread para manter a interface responsiva
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
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            for location in locations:
                if self.stop_requested:
                    break

                for keyword in keywords:
                    if self.stop_requested:
                        break

                    search_query = f"{keyword} em {location}"
                    self.log(f"Buscando: '{search_query}'...")

                    try:
                        url = f"https://www.google.com/maps/search/{search_query.replace(' ', '+')}"
                        await page.goto(url, timeout=60000)
                        await page.wait_for_timeout(3000)

                        # Rola o painel lateral de resultados para carregar os estabelecimentos
                        feed_selector = 'div[role="feed"]'
                        if await page.query_selector(feed_selector):
                            for _ in range(3):
                                if self.stop_requested:
                                    break
                                await page.eval_on_selector(
                                    feed_selector, 
                                    'el => el.scrollBy(0, 1000)'
                                )
                                await page.wait_for_timeout(1500)

                        listings = await page.query_selector_all('a[href*="/maps/place/"]')
                        count = 0

                        for listing in listings:
                            if self.stop_requested or count >= limit:
                                break

                            try:
                                title = await listing.get_attribute('aria-label')
                                link = await listing.get_attribute('href')

                                if title and title not in [l['Nome'] for l in all_leads]:
                                    # Clica no item da lista para abrir o painel de detalhes
                                    await listing.click()
                                    await page.wait_for_timeout(1500)

                                    # Tenta extrair o site oficial do estabelecimento no painel lateral
                                    website_elem = await page.query_selector('a[data-item-id="authority"]')
                                    website = await website_elem.get_attribute('href') if website_elem else None

                                    has_site = "Sim" if website else "Não"
                                    site_url = website if website else "N/A"

                                    all_leads.append({
                                        'Nome': title,
                                        'Categoria': keyword,
                                        'Cidade_Região': location,
                                        'Possui_Site': has_site,
                                        'Website': site_url,
                                        'Link_Maps': link,
                                        'Status_Inicial': 'Pendente Qualificação'
                                    })
                                    count += 1
                            except Exception:
                                continue

                        self.log(f"  -> Encontrados {count} resultados para '{search_query}'")

                    except Exception as e:
                        if self.stop_requested:
                            break
                        self.log(f"Erro ao buscar '{search_query}': {str(e)}")

            await browser.close()

        # Comportamento pós-encerramento ou cancelamento
        if self.stop_requested:
            self.log("\n[CANCELADO] Execução interrompida pelo usuário.")

        if all_leads:
            df = pd.DataFrame(all_leads)
            df.to_csv(filename, index=False, encoding="utf-8-sig")
            
            caminho_completo = os.path.abspath(filename)
            self.log(f"[SUCESSO] Total de {len(all_leads)} leads exportados até o momento.")
            self.log(f"Arquivo salvo em: {caminho_completo}")
            
            if self.stop_requested:
                messagebox.showwarning("Cancelado", f"A busca foi interrompida!\n\nOs {len(all_leads)} leads capturados até o momento foram salvos em:\n{caminho_completo}")
            else:
                messagebox.showinfo("Concluído", f"Captura finalizada!\n\nArquivo salvo com sucesso em:\n{caminho_completo}")
        else:
            self.log("\n[AVISO] Nenhum lead encontrado para exportar.")

        # Restaura os botões para o estado inicial
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = Claudia(root)
    root.mainloop()