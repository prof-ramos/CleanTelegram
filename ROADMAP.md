# ROADMAP - CleanTelegram

**Versão Atual:** 1.1.0
**Última Atualização:** Fevereiro 2026

---

## 📊 Visão Geral

O CleanTelegram é uma ferramenta CLI para gerenciar e limpar contas do Telegram. Este roadmap orienta o desenvolvimento futuro com foco em:

- **Segurança:** Proteção contra perda acidental de dados
- **Performance:** Processamento eficiente de grandes volumes
- **Usabilidade:** Interface intuitiva e documentação clara
- **Qualidade:** Alta cobertura de testes e código confiável

---

## 🎯 Status Atual (v1.1.0)

### Funcionalidades Implementadas

| Funcionalidade | Status | Estabilidade |
|----------------|--------|--------------|
| Limpeza de diálogos | ✅ Completo | Estável |
| Backup de grupos | ✅ Completo | Estável |
| Download de mídia | ✅ Completo | Estável |
| Relatórios (CSV/JSON) | ✅ Completo | Estável |
| Upload para Cloud Chat | ✅ Completo | Estável |
| Modo interativo | ✅ Completo | Estável |
| Modo Bot | ✅ Completo | Estável |

### Métricas Atuais

| Métrica | Valor | Meta |
|---------|-------|------|
| Cobertura de testes | 59% | 70%+ |
| Testes unitários | 28 | 50+ |
| Testes de integração | 0 | 10+ |
| Linhas de código | ~2.000 | - |

---

## 🚅 Curto Prazo (Fevereiro - Março 2025)

### Fase 1: Qualidade e Segurança (1-2 semanas)

**Status:** 🟡 Em Planejamento

#### Infraestrutura de Testes
- [ ] `pytest.ini` com marcadores e configuração
- [ ] `.coveragerc` com fail_under=70
- [ ] AsyncIteratorMock centralizado no conftest.py

#### Componentes Críticos
- [ ] **ui.py** - Testar todas as 9 funções (0% → 70%+)
- [ ] **cli.py** - confirm_action(), env_int(), run_*()
- [ ] Meta: Cobertura geral 59% → 70%+

**Responsável:** Equipe de QA
**Esforço Estimado:** 10-12 horas
**Prioridade:** ALTA

---

### Fase 2: Melhorias de UX (Março 2025)

#### 1. Filtros Avançados de Limpeza

```bash
# Limpar apenas contatos inativos há mais de 6 meses
cleantelegram --clean --filter "inactive>6m"

# Limpar grupos sem mensagens recentes
cleantelegram --clean --filter "groups-no-activity>30d"

# Limpar preservando contatos favoritos
cleantelegram --clean --preserve-favorites
```

**Arquivos:**
- `src/clean_telegram/filters.py` (novo)
- `src/clean_telegram/cli.py` (atualização)

#### 2. Modo de Recuperação (Undo)

```bash
# Reverter última limpeza (limitado a 24h)
cleantelegram --undo-last-clean

# Listar operações recentes
cleantelegram --history
```

**Arquivos:**
- `src/clean_telegram/history.py` (novo)
- `src/clean_telegram/undo.py` (novo)

#### 3. Configuração por Arquivo

```bash
# Usar arquivo de configuração
cleantelegram --config cleaning-rules.toml

# Exemplo de cleaning-rules.toml:
[preservar]
ids = [123456789, 987654321]
names = ["Trabalho*", "Família"]

[limpar]
inactive_days = 180
groups_without_messages = 90
```

**Arquivos:**
- `src/clean_telegram/config.py` (novo)
- `.cleantelegram.toml` (exemplo)

**Esforço Estimado:** 16-20 horas
**Prioridade:** MÉDIA

---

## 🎯 Médio Prazo (Abril - Junho 2025)

### Fase 3: Testes de Integração (Abril 2025)

**Status:** 🔴 Deferido (20h+ de trabalho)

#### Testes com Telegram Real
- [ ] Conta de teste dedicada
- [ ] Testes de backup real
- [ ] Testes de limpeza controlada
- [ ] Testes de upload para cloud
- [ ] Mock de respostas da API

**Arquivos:**
- `tests/integration/test_telegram_api.py` (novo)
- `tests/integration/conftest.py` (novo)

**Esforço Estimado:** 20-24 horas
**Prioridade:** MÉDIA

---

### Fase 4: Performance e Escala (Maio 2025)

#### 1. Download Paralelo Otimizado

```python
# Implementar:
- Adaptive concurrency (ajusta conforme latência)
- Progresso por chunk
- Retomada de sessão
- Cache de arquivos já baixados
```

**Arquivos:**
- `src/clean_telegram/parallel.py` (novo)
- `src/clean_telegram/cache.py` (novo)

#### 2. Exportação Incremental

```bash
# Exportar apenas mensagens desde o último backup
cleantelegram --backup-group -1001234567890 --incremental

# Criar checkpoint de progresso
cleantelegram --backup-group -1001234567890 --checkpoint
```

**Arquivos:**
- `src/clean_telegram/incremental.py` (novo)
- `src/clean_telegram/checkpoint.py` (novo)

#### 3. Compressão de Backups

```bash
# Comprimir backup após download
cleantelegram --backup-group -1001234567890 --compress

# Formatos suportados: zip, tar.gz, zst
cleantelegram --backup-group -1001234567890 --compress-format zst
```

**Arquivos:**
- `src/clean_telegram/compress.py` (novo)

**Esforço Estimado:** 24-28 horas
**Prioridade:** MÉDIA

---

### Fase 5: Analytics e Relatórios (Junho 2025)

#### 1. Análise de Atividade

```bash
# Relatório de atividade por contato
cleantelegram --analyze activity --by-contacts --period 90d

# Grupos mais ativos
cleantelegram --analyze groups --top 20 --by-messages

# Horários de pico
cleantelegram --analyze patterns --heatmap hourly
```

**Arquivos:**
- `src/clean_telegram/analytics.py` (novo)
- `src/clean_telegram/patterns.py` (novo)

#### 2. Exportação HTML

```bash
# Gerar visualização HTML do chat
cleantelegram --backup-group -1001234567890 --export-html

# Incluir mídia embedada
cleantelegram --backup-group -1001234567890 --export-html --embed-media
```

**Arquivos:**
- `src/clean_telegram/html_export.py` (novo)
- `templates/chat.html` (novo)

#### 3. Dashboard Web (Opcional)

```bash
# Iniciar dashboard local
cleantelegram --dashboard --port 8080

# Visualizar backups, relatórios e analytics
```

**Arquivos:**
- `src/clean_telegram/web/` (novo diretório)
- `src/clean_telegram/web/app.py` (novo)

**Esforço Estimado:** 32-40 horas
**Prioridade:** BAIXA

---

## 🔭 Longo Prazo (Julho - Dezembro 2025)

### Fase 6: CI/CD e Automação (Julho 2025)

#### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
- Testes automáticos em cada PR
- Cobertura de código (Codecov)
- Linting (ruff, mypy)
- Release automático
```

**Arquivos:**
- `.github/workflows/test.yml` (novo)
- `.github/workflows/release.yml` (novo)
- `ruff.toml` (novo)
- `mypy.ini` (novo)

#### Docker Support

```bash
# Usar via Docker sem instalar
docker run --rm -v ./backups:/data cleantelegram --backup-group ...

# Docker com persistência de sessão
docker run -v ./session:/app/session cleantelegram --interactive
```

**Arquivos:**
- `Dockerfile` (novo)
- `docker-compose.yml` (novo)

**Esforço Estimado:** 12-16 horas
**Prioridade:** MÉDIA

---

### Fase 7: Multi-Conta e Sincronização (Agosto 2025)

#### Gerenciamento Multi-Conta

```bash
# Adicionar múltiplas contas
cleantelegram --account add --name "pessoal"
cleantelegram --account add --name "trabalho"

# Usar conta específica
cleantelegram --account trabalho --backup-group -1001234567890

# Listar contas configuradas
cleantelegram --account list
```

**Arquivos:**
- `src/clean_telegram/accounts.py` (novo)
- `src/clean_telegram/multi_session.py` (novo)

#### Sincronização entre Contas

```bash
# Sincronizar backups entre contas
cleantelegram --sync --from pessoal --to trabalho

# Mesclar backups de múltiplas contas
cleantelegram --merge-backups --accounts pessoal,trabalho --output merged.json
```

**Arquivos:**
- `src/clean_telegram/sync.py` (novo)

**Esforço Estimado:** 24-28 horas
**Prioridade:** BAIXA

---

### Fase 8: Recursos Avançados (Setembro - Dezembro 2025)

#### 1. Busca e Filtros Inteligentes

```bash
# Buscar mensagens por conteúdo
cleantelegram --search "projeto X" --in-groups --period 2024-01..2024-12

# Exportar resultado da busca
cleantelegram --search "documentos importantes" --export search-results.json

# Busca com expressões regulares
cleantelegram --search-regex "\b[A-Z]{2}-\d{4}\b" --pattern "ticket numbers"
```

**Arquivos:**
- `src/clean_telegram/search.py` (novo)

#### 2. Deduplicação de Mensagens

```bash
# Detectar mensagens duplicadas
cleantelegram --deduplicate --group -1001234567890

# Remover duplicatas automaticamente
cleantelegram --deduplicate --group -1001234567890 --auto-remove
```

**Arquivos:**
- `src/clean_telegram/dedup.py` (novo)

#### 3. Agenda de Tarefas

```bash
# Agendar limpeza recorrente
cleantelegram --schedule --clean --filter "inactive>90d" --cron "0 0 * * 0"

# Agendar backup semanal
cleantelegram --schedule --backup-group -1001234567890 --cron "0 2 * * 0"

# Listar tarefas agendadas
cleantelegram --schedule --list
```

**Arquivos:**
- `src/clean_telegram/scheduler.py` (novo)

**Esforço Estimado:** 40-48 horas
**Prioridade:** BAIXA

---

## 📈 Métricas de Sucesso

### Qualidade de Código
| Métrica | Atual | Q1 2025 | Q2 2025 |
|---------|-------|---------|---------|
| Cobertura de testes | 59% | 70% | 85% |
| Testes de integração | 0 | 5 | 15+ |
| Linting passando | ❌ | ✅ | ✅ |
| Type hints (mypy) | 0% | 50% | 80% |

### Performance
| Métrica | Atual | Meta |
|---------|-------|------|
| Download paralelo | 5 concurrent | 10-20 adaptive |
| Export incremental | ❌ | ✅ |
| Compressão | ❌ | ✅ |
| Cache de sessão | ❌ | ✅ |

### Funcionalidades
| Categoria | Atual | Q1 2025 | Q2 2025 |
|-----------|-------|---------|---------|
| Core features | 7 | 7 | 9 |
| Filtros | 0 | 3+ | 8+ |
| Analytics | 0 | 0 | 4+ |
| Automation | 0 | 0 | Scheduler |

---

## 🤝 Contribuição

### Áreas para Contribuição

1. **Documentação** - Tutoriais, exemplos de uso, traduções
2. **Testes** - Casos de teste, mocks de fixtures
3. **UI/UX** - Melhorias no modo interativo, mensagens de erro
4. **Performance** - Otimizações, caching, parallel processing
5. **Integrações** - Cloud storage (S3, GDrive), notificações

### Como Contribuir

1. Abra uma issue discutindo a feature
2. Aguarde aprovação dos mantenedores
3. Fork e implemente seguindo o padrão de código
4. Adicione testes para novas funcionalidades
5. Submeta PR com descrição clara

---

## 📝 Notas

- Prioridades podem mudar conforme feedback da comunidade
- Features marcadas como "Opcionais" dependem de disponibilidade
- Fases podem sobrepor temporalmente
- Decision record em `docs/ADR/` para decisões arquiteturais

---

**Última Revisão:** Fevereiro 2025
**Próxima Revisão:** Abril 2025
