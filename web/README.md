# hiveBr Web

Versão do simulador hiveBr que roda inteiramente no navegador. O Python escrito
pelo usuário é interpretado no cliente com Pyodide (WebAssembly) e importa o
pacote `hivebr` real, sem alterações. Não há servidor de simulação: a aplicação
é um site estático.

A camada pygame é substituída por stubs em `web/python/pygame/`, que não
desenham nada. Física, LiDAR, waypoints, colisões e logger são os mesmos da
versão desktop. A arquitetura está descrita em [ARCHITECTURE.md](ARCHITECTURE.md).

## Requisitos

- Node.js 18 ou superior (exigido pelo Vite 6).
- Navegador com WebAssembly. SharedArrayBuffer só é necessário para comandos
  ao vivo (ver [Hospedagem estática](#hospedagem-estática)).
- Conexão com a internet na primeira carga, para baixar o Pyodide e os pacotes.

## Como rodar

```bash
cd web
npm install
npm run dev       # servidor de desenvolvimento
npm run build     # gera web/dist/
npm run preview   # serve web/dist/ localmente
```

`dev`, `build` e `preview` executam antes `npm run bundle`, que empacota
`src/hivebr`, `config/`, `examples/`, `web/templates/` e `web/python/` em
`public/hivebr-py.zip`. Esse arquivo é gerado e está no `.gitignore`.

**Rede.** A página baixa do CDN jsDelivr o runtime do Pyodide, versão 0.29.0
(fixada em `src/runtime/client.js`), e os pacotes numpy, pyyaml e pillow. O
scipy é carregado em seguida, em segundo plano. Para auto-hospedar o Pyodide,
defina `VITE_PYODIDE_URL` (variável de ambiente ou `web/.env`) com a URL de uma
cópia completa da distribuição do Pyodide 0.29.0. A barra final é acrescentada
se faltar.

## Como usar

**Interface.**

- Menu superior: Arquivo, Editar, Exibir, Simulação, Exemplos e Ajuda.
- Esquerda: Navegador, com o script atual, a cena, os arquivos gerados e as ferramentas.
- Centro: canvas da simulação, com a barra de ferramentas (Selecionar, Waypoint,
  Obstáculo, Recarga, Mover robô, Desenhar pista) e o menu Camadas (grade,
  rastros, LiDAR, waypoints, rótulos, ligações entre robôs).
- Direita: editor de código. `Ctrl+Enter` executa.
- Inferior: Console, Telemetria e Problemas.
- Janelas: Parâmetros (`P`), Gráficos (`G`) e Mapa (`K`).

A lista completa de atalhos está em Ajuda (`?`). `Espaço` inicia ou pausa a
simulação. Se ela não começar sozinha após a execução, use Iniciar.

**Demonstração.** Menu Simulação > Demonstração. Seis B-bots fazem duas
patrulhas, com obstáculos, LiDAR e comunicação limitada. Roda em loop até parar.

**Exemplos.** Menu Exemplos > Galeria de exemplos. O catálogo fica em
`web/src/examples/catalog.js`:

- Tutoriais (`web/templates/`): Início rápido, Enxame descentralizado, Formação
  centralizada, Seguidor de linha com PID, Robô holonômico e LiDAR com desvio de
  obstáculos.
- Exemplos do repositório (`examples/`): Controle Kanayama, Enxame descentralizado,
  Seguidor de linha, Vários seguidores de linha, Frota de robôs diferenciais,
  Robô hexagonal holonômico e Seguidor de linha hexagonal.

**Escrever um script mínimo.** Um B-bot diferencial que percorre uma rota de
waypoints, com o mesmo padrão do exemplo Início rápido:

```python
import numpy as np
from hivebr import HiveBrAgent, SwarmExperiment
from hivebr.engine import load_config


class IrAoWaypoint(HiveBrAgent):
    def loop(self, state, neighbors):
        alvo = state.goal  # waypoint atual; None quando a rota terminou
        if alvo is None:
            return (0.0, 0.0)  # (v, omega)
        erro = np.arctan2(alvo[1] - state.y, alvo[0] - state.x) - state.theta
        return (0.3 * max(0.0, np.cos(erro)), 1.5 * np.sin(erro))


config = load_config("config/default.yaml")
frota = [{"id": 0, "type": "differential", "initial_pose": [2.0, 2.0, 0.0], "radius": 0.25}]
exp = SwarmExperiment(robots=frota, backend="navsim2d", config=config, orientation=False)
exp.assign_agent(robot_id=0, agent_class=IrAoWaypoint)
exp.assign_route(0, [(6.0, 2.0), (14.0, 2.0), (14.0, 8.0), (6.0, 8.0)])
exp.run()  # bloqueia até a simulação parar; o código abaixo executa depois
print("fim da rota")
```

`exp.run()` bloqueia até a simulação parar, e o código depois dele é executado
em seguida. O método `loop` recebe o estado do robô (`x`, `y`, `theta`, `goal`)
e devolve `(v, omega)`.

## Idiomas (pt-BR e en)

A interface vem em português (Brasil) e inglês, sem dependências extras. O idioma
inicial vem do navegador: qualquer variante de português (`pt`, `pt-PT`…) usa
pt-BR e todo o resto usa inglês. Para escolher à mão, use **Arquivo › Idioma**
(também em **Ajuda › Idioma**): *Automático (navegador)*, *Português (Brasil)* ou
*English*. A troca é imediata, não interrompe uma simulação em andamento, não
mexe nos seus scripts e fica salva no navegador (`hivebr.web.locale.v1`).

- Dicionários: `src/i18n/pt-BR.js` e `src/i18n/en.js`, com as mesmas chaves;
  `src/i18n/index.js` tem `t(chave, params)`, `tn` (plural), formatação de números
  por idioma (`Intl`) e a detecção.
- Avisos do Python e do worker trazem `code` + `params` (e o texto em inglês como
  reserva); a interface traduz pelo `code`.
- Exemplos: os tutoriais e a demonstração têm versão em inglês em `templates/en/`
  (mesma lógica; só mudam comentários, docstrings e textos impressos). Os exemplos
  de `examples/` aparecem como estão no repositório, com comentários em português.
  Novos scripts em branco seguem o idioma atual; abas já abertas nunca são reescritas.
- **Limite conhecido:** o que o pacote `hivebr` imprime (por exemplo as mensagens do
  `DataLogger`, em português) vem do pacote original, sem modificação, e não é traduzido.

## Diferenças em relação ao desktop

- **Sem multiprocessing nem threads.** Tudo roda em um único Web Worker. Por
  isso `decentralized_multiprocess.py` (que usa `ProcessPoolExecutor`) não está
  no catálogo.
- **`run_holonomic.py` não está no catálogo.** Depende do módulo `vortex_apf`,
  que não existe no repositório.
- **Sem janela pygame.** A cena é desenhada em canvas 2D e controlada pela interface.
- **Desenhos customizados.** Só são exibidos através de `draw_callback`. As
  chamadas `pygame.draw.line`, `lines`, `circle`, `polygon` e `rect` (e as
  variantes `aaline` e `aalines`) são capturadas. `ellipse` e `arc` não desenham,
  e texto não é desenhado. Por isso o painel de texto do exemplo de seguidor de
  linha hexagonal não aparece.
- **Figuras do matplotlib.** `plt.show()` gera uma figura na aba Figuras da
  janela Gráficos. `plt.savefig()` não gera figura na interface.
- **Arquivos.** CSV, PKL, YAML e o PNG da pista são baixados pelo navegador.
- **Primeira carga.** O navegador baixa o runtime e os pacotes da seção Rede.
  A execução só começa depois do download.

## Hospedagem estática

`npm run build` gera `web/dist/` com `base: './'`, então os caminhos são
relativos e a pasta pode ser servida em subcaminho. Basta publicar o conteúdo
de `dist/`.

Comandos ao vivo (pausar, adicionar waypoints, alterar parâmetros durante a
execução) exigem isolamento entre origens (`crossOriginIsolated`). Há duas formas:

- **Cabeçalhos no servidor.** Envie `Cross-Origin-Opener-Policy: same-origin`
  e `Cross-Origin-Embedder-Policy: require-corp`. `dev` e `preview` já enviam
  esses cabeçalhos.
- **Sem cabeçalhos (por exemplo, GitHub Pages).** O build copia
  `public/coi-sw.js` para `dist/`. Esse service worker adiciona os cabeçalhos às
  respostas. Na primeira visita a página recarrega uma vez. Isso exige contexto
  seguro: HTTPS ou `localhost`.

Sem isolamento, a simulação executa normalmente, mas os comandos ao vivo não
funcionam. A interface mostra um aviso de modo limitado, e Parar encerra o
worker à força.

## Docker

O `web/Dockerfile` tem duas etapas. A primeira (`node:24-alpine`) roda `npm ci`
e `npm run build`. A segunda (`nginxinc/nginx-unprivileged`) serve só
`web/dist/` na porta 8080, sem root. O contexto de build é a raiz do repositório,
porque o build lê `src/hivebr`, `config/` e `examples/`. O `.dockerignore` da raiz
exclui `**/PRIVADO-*`, `node_modules`, `dist` e os testes.

```bash
# a partir da raiz do repositório
HIVEBR_BIND=127.0.0.1:3060 docker compose -f web/docker-compose.yml up -d --build
curl -I http://127.0.0.1:3060/healthz
docker compose -f web/docker-compose.yml down
```

`HIVEBR_BIND` define o endereço:porta publicado no host. Se não for definido, o
padrão é `172.16.0.1:3060`. Para acesso só local, use `127.0.0.1`.

O nginx envia os cabeçalhos COOP e COEP em todas as respostas, inclusive
arquivos estáticos e erros. `/assets/` tem cache de um ano e imutável. `index.html`,
`coi-sw.js` e `hivebr-py.zip` usam `no-cache`. `/healthz` responde 200 e é o
endpoint do healthcheck. O contêiner roda com sistema de arquivos somente leitura
(`/tmp` é tmpfs), `cap_drop: ALL`, `no-new-privileges` e limite de 128 MB de memória.

### Deploy automático no servidor

`web/deploy/` tem um deploy por *pull*: um timer do systemd consulta o GitHub a
cada 30 minutos e, se a branch acompanhada recebeu commits, atualiza o clone e roda
`docker compose up -d --build`. Não abre porta de entrada nem guarda segredos.
Se o build falhar, o contêiner anterior continua no ar e o mesmo commit não é
tentado de novo até haver outro.

```bash
# no servidor, com o repositório clonado em /docker/hivebr
install -m 755 web/deploy/hivebr-deploy.sh /usr/local/bin/
install -m 644 web/deploy/hivebr-deploy.{service,timer} /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now hivebr-deploy.timer

journalctl -u hivebr-deploy -n 30      # histórico
systemctl list-timers hivebr-deploy    # próxima verificação
hivebr-deploy.sh --force               # reimplanta o commit atual
```

A branch acompanhada fica em `Environment=HIVEBR_BRANCH=` no `hivebr-deploy.service`
(hoje `feature/browser-simulator`; troque para `main` quando for integrada).
Depois de alterar os arquivos em `web/deploy/`, copie-os de novo como acima.

## Testes

Execute a partir de `web/`:

```bash
python3 python/tests/run_all.py          # testes Python (runtime, comandos, robôs, exemplos)
python3 python/tests/run_all.py trecho   # só os testes cujo nome contém "trecho"
npm run test:runtime                     # testes do buffer de comandos (tests/runtime/ring.test.mjs)
npm run test:e2e                         # página completa no Chromium
npm run test:app                         # interface completa (build de produção em /hivebr/, sem COOP/COEP, Pyodide real)
npm run test:i18n                        # chaves iguais em pt-BR/en, chaves usadas existem, sem texto fixo em português
npm run test:tokens                      # contraste (WCAG) dos tokens de cor nos dois temas
```

`npm run test:e2e` sobe o Vite nas portas 5199 e 5198 e usa o Chromium em
`/usr/bin/chromium-browser`, caminho fixo em `tests/runtime/e2e-runtime.mjs`.
Ajuste esse caminho se o navegador estiver em outro lugar.

`npm run test:app` compila o site, serve `dist/` por um servidor estático em
`/hivebr/` sem cabeçalhos COOP/COEP (exercita `coi-sw.js` e a base relativa) e
conduz a interface real com playwright-core. Precisa de rede para o Pyodide.
Capturas de tela vão para `E2E_SHOTS` (padrão: pasta temporária do sistema). Os
fluxos fixam o idioma em pt-BR; há fluxos próprios para en-US, fr-FR, a troca ao vivo
em Arquivo › Idioma e uma varredura em inglês que procura português sobrando.
Também exercitam as janelas flutuantes (limites, alças, empilhamento, teclado).

## Estrutura

```
web/
  src/           interface Vue 3: componentes, canvas, estado e catálogo de exemplos
  src/runtime/   worker com Pyodide, cliente e buffer de comandos (SharedArrayBuffer)
  python/        stubs (pygame, pygame_gui, tkinter) e pacote hivebr_web (host, simulador, comandos)
  templates/     exemplos feitos para o navegador
  public/        coi-sw.js (isolamento sem cabeçalhos) e o zip gerado
  scripts/       bundle-python.mjs, que gera public/hivebr-py.zip
  src/i18n/      dicionários pt-BR e en, t(), detecção de idioma
  templates/en/  versões em inglês dos tutoriais e da demonstração
  tests/         testes de JavaScript (ring, i18n, tokens) e end-to-end
  ARCHITECTURE.md
```
