$(document).ready(function() {
    $('.mb-3').removeClass('mb-3');
    let REGRAS = {};
    let DADOS_FILIAL = {};
    $('#id_logo').on('change', function () {
        if (this.files && this.files[0]) {
            const url = URL.createObjectURL(this.files[0]);
            $('#logo-preview').attr('src', url);
        }
    });
    function carregarRegras() {
        return $.getJSON('/regras_produto/js/', function (data) {
            REGRAS = data;
            console.log('Regras carregadas:', REGRAS);
        });
    }
    function carregarDadosFilial() {
        return $.getJSON('/filiais/js/', function (data) {
            DADOS_FILIAL = data;
            const texto = Object.entries(DADOS_FILIAL).map(([id, f]) =>
                `Filial ${id}:
                Cliente P.: ${f.cli ?? '-'}
                Técnico P.: ${f.tec ?? '-'}
                Vendedor P.: ${f.vend ?? '-'}
                Multi M2: ${f.multi_m2 ?? '-'}
                `).join('\n\n');
            console.log(texto);
        });
    }
    function getTabelaPreco() {return $('#id_tabela_preco').val();}
    // Função otimizada Select2
    function rendOpt(d){return !d.id ? d.text : $(`<div style="display:flex;flex-direction:column;line-height:1.2"><span style="font-size:14px">${d.id}</span><br><strong style="font-size:14px">${d.text}</strong></div>`);}
    function renderRegra(d){return !d.id ? d.text : $(`<div style="display:flex;flex-direction:column;line-height:1.2"><small class="text-muted">${d.codigo}</small><strong>${d.text}</strong></div>`);}
    const lingSel = {inputTooShort: ()=>'Por favor, insira 1 ou mais caracteres', noResults: ()=>'Nenhum resultado encontrado', searching: ()=>'Procurando...'};
    function ajSel2(url){return {url, dataType:'json', delay:250, data:p=>({term:p.term}), processResults: d => {return {results: d.results};},cache:true};}
    function ajaxRegras(url){return {url, dataType: 'json', delay: 250, data: p => ({ term: p.term }), processResults: d => {return {results: d.results};}, cache: true};}
    function focSel2() {
        setTimeout(function () {
            const campo = document.querySelector('.select2-container--open .select2-search__field');
            if (campo) {campo.focus();}
        }, 50);
    }
    const opSel = "Escolha uma opção";
    carregarRegras();
    carregarDadosFilial();
    function criarItemManager() {
        return {
            data: {},
            currentEditing: { porta: null, itemId: null, $tr: null },
            ensurePorta(porta) {if (!this.data[porta]) this.data[porta] = [];},
            setEditingItem($tr) {
                this.currentEditing = {porta: Number($tr.data('porta')), itemId: Number($tr.data('item-id')), $tr};
            },
            addItem(porta, item) {
                this.ensurePorta(porta);
                item.id = Date.now();
                item.qtd_manual = false;
                this.data[porta].push(item);
                return item.id;
            },
            updateEditingItem(cells) {
                const { porta, itemId, $tr } = this.currentEditing;
                const item = this.data[Number(porta)]?.find(i => i.id === itemId);
                if (!item) return;
                const novoCod  = cells[0];
                const novaDesc = cells[1];
                const novaUnid = cells[2];
                const novoVl   = parseFloat(cells[3]) || 0;
                const novaQtd  = parseFloat(cells[4]);
                const mudou = item.cod !== novoCod || item.desc !== novaDesc || item.unid !== novaUnid || item.vl_unit !== novoVl || (!isNaN(novaQtd) && Number(item.qtd_final ?? 0) !== novaQtd);
                if (!mudou) return;
                item.cod = novoCod; item.desc = novaDesc;
                item.unid = novaUnid; item.vl_unit = novoVl;
                if (!isNaN(novaQtd)) {
                    item.qtd_final  = novaQtd;
                    item.qtd_manual = true;
                    item.ativo      = novaQtd > 0;
                }
                $tr.find('.td-cod').text(item.cod);
                $tr.find('.td-desc').text(item.desc);
                $tr.find('.td-unid').text(item.unid);
                $tr.find('.vl-unit').text(item.vl_unit.toFixed(2));
                $tr.find('.qtd-produto').text(item.qtd_final.toFixed(2));
                atualizarTabelaPorta(porta);
                atualizarSubtotal();
                atualizarJSONPortas();
            },
            removeItemById(porta, itemId) {
                if (!this.data[porta]) return;
                this.data[porta] = this.data[porta].filter(i => i.id !== itemId);
            },
            resetPorta(porta) { this.data[porta] = []; },
            clearEditing() {this.currentEditing = { porta: null, itemId: null, $tr: null };}
        };
    }
    const prodManager    = criarItemManager();
    const prodAdcManager = criarItemManager();
    function montarTrProduto({ porta, item, modalEditar, regraOrigem = '' }) {
        const fmt = v => Number(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const totCompra = (item.qtd_final * item.vl_compra);
        const vlTotal   = (item.qtd_final * item.vl_unit);
        const regraAttr = regraOrigem ? `data-regra-origem="${regraOrigem}"` : '';
        return `
            <tr data-porta="${porta}" data-item-id="${item.id}" ${regraAttr}>
                <td class="td-cod mobile-full">${item.cod}</td>
                <td class="td-desc mobile-full">${item.desc}</td>
                <td class="td-unid mobile-full">${item.unid}</td>
                <td class="td-vl-compra text-danger fw-bold mobile-full">${fmt(item.vl_compra)}</td>
                <td class="vl-unit text-success fw-bold mobile-full">${fmt(item.vl_unit)}</td>
                <td class="qtd-produto mobile-full">${fmt(item.qtd_final)}</td>
                <td class="tot-compra text-danger fw-bold mobile-full">${fmt(totCompra)}</td>
                <td class="vl-total text-success fw-bold mobile-full">${fmt(vlTotal)}</td>
                <td class="mobile-full">
                    <button class="btn btn-success btn-sm editBtn" data-bs-target="#${modalEditar}"><i class="fa-regular fa-pen-to-square text-white"></i></button>
                    <button class="btn btn-danger btn-sm deleteBtn"><i class="fa-solid fa-trash-can text-white"></i></button>
                </td>
            </tr>
        `;
    }
    function getPortasFromBackend() {
        const el = document.getElementById('json-portas');
        if (!el) return [];
        let raw = el.textContent || el.innerText || '';
        raw = raw.trim();
        if (!raw || raw === 'None') return [];
        try {
            const parsed = JSON.parse(raw);
            if (Array.isArray(parsed)) return parsed;
            if (typeof parsed === 'string') {
                const reparsed = JSON.parse(parsed);
                return Array.isArray(reparsed) ? reparsed : [];
            }
            return [];
        } catch (e) {
            console.error('Erro ao parsear portas_json', e, raw);
            return [];
        }
    }
    portasJSON = getPortasFromBackend();
    console.log('portasJSON:', portasJSON);
    hidratarManagers(portasJSON.length ? portasJSON : [{ numero: 1, produtos: [], adicionais: [] }]);
    calcTotalEntrada();
    calcTotalPedido();
    $('.table').addClass("table-sm");
    $('[name^="nome_"]').first().focus();
    $('[name^="descricao"]').first().focus();
    // Função do Toastify
    let cor_verde = "linear-gradient(to right, #00b09b, #96c93d)";
    let cor_vermelho = "linear-gradient(to right, #ff416c, #ff4b2b)";
    let cor_amarelo = "linear-gradient(to right, #ff9f00, #ff6f00)";
    let cor_info = "linear-gradient(to right, #02202B, #017AB1)";
    let cor_padrao = "linear-gradient(to right, #333, #555)";
    // Ícones do Toast
    let ic_verde = "<i class='fa-solid fa-circle-check'></i>";
    let ic_vermelho = "<i class='fa-solid fa-circle-xmark' style='float: none; color: white; margin: 0;'></i>";
    let ic_amarelo = "<i class='fa-solid fa-triangle-exclamation'></i>";
    let ic_info = "<i class='fa-solid fa-circle-exclamation'></i>";
    let ic_padrao = "<i class='fa-solid fa-hourglass-end'></i>";
    function toast(msg, cor="#333") {
        Toastify({text: msg, duration: 5000, gravity: "top", position: "center", style:{background: cor}, stopOnFocus: true, escapeMarkup: false,
            onClick: function () {
                let toastElements = document.querySelectorAll(".toastify");
                toastElements.forEach(el => {
                    el.style.transition = "opacity 0.5s ease-out";
                    el.style.opacity = "0";
                    setTimeout(() => el.remove(), 500);
                });
            },
        }).showToast();
    }
    $(document).on('submit', '.form-excluir', function(e){
        const $form = $(this);
        const $modal = $form.closest('.modal');
        const modal = bootstrap.Modal.getInstance($modal[0]);
        const $btn = $form.find('.btn-confirmar');
        $btn.prop('disabled', true).text('Excluindo...');
        if(modal){modal.hide();}
        setTimeout(function(){
            if($('.modal-backdrop').length === 0){$('body').append('<div id="fake-backdrop" class="modal-backdrop fade show"></div>');}
            $('body').css('pointer-events','none');
        }, 150);
    });
    // Habilitar campo de portão social
    $('#id_portao_social').on('change', function () {
        const p_social = $(this).val();
        if (p_social === 'Não') {
            $("#id_vl_p_s").val('0');
            $("#id_vl_p_s").prop("disabled", true);
            atualizarSubtotal();
        } else if (p_social === "Sim") {$("#id_vl_p_s").prop("disabled", false);}
    });
    $("#id_vl_p_s").on("blur", function() {atualizarSubtotal();});
    // Clicar no EDIT
    $(document).on("click", ".edit-status", function () {
        const id = $(this).data("id");
        const $select = $(`#sel-status-${id}`);
        const $cancel = $(`#cancel-status-${id}`);
        if ($select.prop("disabled")) {
            $select.prop("disabled", false);
            $select.css("background-color", "white");
            $cancel.show();
            return; // primeira etapa concluída
        }
        const novoStatus = $select.find("option:selected").text();
        $(`#novoStatusTexto${id}`).text(novoStatus);
        const modal = new bootstrap.Modal(document.getElementById(`modalConfirmacaoStatus${id}`));
        modal.show();
    });
    // Clicar no CANCELAR
    $(document).on("click", ".fa-circle-xmark", function () {
        const id = $(this).data("id");
        const $select = $(`#sel-status-${id}`);
        $select.prop("disabled", true);
        $select.css("background-color", "#A9A9A9");
        $(this).hide(); // esconder cancelar
    });
    // CONFIRMAR no modal
    $(document).on("click", ".confirm-status", function () {
        const modalElement = $(this).closest(".modal").attr("id");
        const id = modalElement.replace("modalConfirmacaoStatus", "");
        const $select = $(`#sel-status-${id}`);
        const novoStatus = $select.val();
        $.ajax({
            url: "/orcamentos/alterar-status/", method: "POST", data: {id: id, status: novoStatus, csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val()},
            success: function () {
                iniciarLoading();
                toast(`${ic_verde} Status atualizado com sucesso!`, cor_verde);
                $select.prop("disabled", true);
                $(`#cancel-status-${id}`).hide();
                const bsModal = bootstrap.Modal.getInstance(document.getElementById(`modalConfirmacaoStatus${id}`));
                const resumoModal = bootstrap.Modal.getInstance(document.getElementById(`infoEntModal`));
                bsModal.hide();
                resumoModal.hide();
                setTimeout(function () {
                    window.location.href = `/orcamentos/lista/?s=${id}&sit=Faturado`;
                }, 1500);
            },
            error: function () {toast(`${ic_vermelho} Erro ao atualizar o status!`, cor_vermelho);}
        });
    });
    $(function () {$('[data-bs-toggle="tooltip"]').each(function () {new bootstrap.Tooltip(this);});});
    // Novo Teste
    const tiposRegras = {
        qtd: [{ name: 'qtd_expr', label: 'Qtd (fórmula)', type: 'text' }],
        peso: [{ name: 'max', label: 'Máx', type: 'number' }, { name: 'qtd_expr', label: 'Qtd (fórmula)', type: 'text' }],
        simples: [{ name: 'campo', label: 'Campo', type: 'text' }, { name: 'valor', label: 'Valor', type: 'text' }, { name: 'tem_pintura', label: 'É Pintura?', type: 'select' },
            { name: 'qtd_expr', label: 'Qtd (fórmula)', type: 'text' }]
    };
    const CAMPOS_CONTEXTO = [
        { value: 'tipo_lamina', label: 'Tipo da Lâmina' },{ value: 'tipo_pintura', label: 'Tipo de Pintura' },{ value: 'peso', label: 'Peso' },
        { value: 'larg_c', label: 'Largura Corte' },{ value: 'alt_c', label: 'Altura Corte' }
    ];
    function controlarVisibilidadeRegra() {
        const tipoSelecionado = $('#id_tipo').val();
        if (tipoSelecionado === 'SELECAO' || tipoSelecionado === 'QTD') {
            $('#bloco-regras-selecao').show();
            $('#div_id_produto').hide();
        } else {
            $('#bloco-regras-selecao').hide();
            $('#tabela-regras thead').empty();
            $('#tabela-regras tbody').empty();
            $('#div_id_produto').show();
            $('#id_expressao_json').val('');
        }
    }
    $('#id_tipo').on('change', function () {
        const tipo = $(this).val();
        if (tipo === 'QTD') {
            $('#id_tipo_regra').val('qtd').trigger('change');
            $('#id_tipo_regra').closest('.form-group').hide();
        } else {
            $('#id_tipo_regra').closest('.form-group').show();
        }
        controlarVisibilidadeRegra();
    });
    controlarVisibilidadeRegra();
    const tipoSelecionado = $('#id_tipo').val();
    if (tipoSelecionado === 'SELECAO' || tipoSelecionado === 'QTD') {carregarJSONReg();}
    function montarTabela(tipo) {
        const colunas = tiposRegras[tipo] || [];
        let thead = '<tr>';
        colunas.forEach(c => {thead += `<th>${c.label}</th>`;});
        thead += '<th>Produto</th><th></th></tr>';
        $('#tabela-regras thead').html(thead);
        $('#tabela-regras tbody').html('');
    }
    function novaLinha(tipo) {
        const colunas = tiposRegras[tipo] || [];
        let tds = '';
        colunas.forEach(c => {

            if (c.name === 'campo') {
                let options = CAMPOS_CONTEXTO.map(campo =>
                    `<option value="${campo.value}">${campo.label}</option>`
                ).join('');

                tds += `
                    <td>
                        <select class="campo form-control form-control-sm">
                            <option value="">Selecione</option>
                            ${options}
                        </select>
                    </td>
                `;

            } else if (c.name === 'tem_pintura') {

                // 🔥 AQUI resolve o problema
                tds += `
                    <td>
                        <select class="tem_pintura form-control form-control-sm">
                            <option value="">-- Selecione --</option>
                            <option value="true">Sim</option>
                            <option value="false">Não</option>
                        </select>
                    </td>
                `;

            } else {
                tds += `<td><input type="${c.type}" class="${c.name} form-control form-control-sm"></td>`;
            }
        });
        tds += `
            <td><select class="produto form-control" style="width:100%"></select></td>
            <td><button type="button" class="btn btn-danger btn-sm remover"><i class="fa-solid fa-trash-can text-white"></i></button></td>
        `;
        return `<tr>${tds}</tr>`;
    }
    function iniciarSelect2(context = document) {
        $(context).find('.produto').select2({placeholder: 'Buscar produto...',minimumInputLength: 1,allowClear: true,language: lingSel,width: '100%',
            ajax: {url: '/produtos/lista_ajax1/', dataType: 'json', delay: 250, data: function (params) { return { term: params.term }; }, processResults: function (data) {return {results: data.results};}, cache: true}
        }).on('select2:open', focSel2);
    }
    function gerarJSON() {
        const tipoSistema = $('#id_tipo').val();
        const tipo = $('#id_tipo_regra').val();
        let dados = [];
        $('#tabela-regras tbody tr').each(function () {
            let produtoSelect = $(this).find('.produto');
            let qtd_expr = $(this).find('.qtd_expr').val();
            if (!produtoSelect.val()) return;
            // 🔥 QTD
            if (tipoSistema === 'QTD') {
                dados.push({produto_id: produtoSelect.val(), desc_prod: produtoSelect.find('option:selected').text(), qtd_expr: qtd_expr});
            }
            // 🔥 SELECAO (mantém como já está)
            else if (tipoSistema === 'SELECAO') {
                let condicoes = {};
                const colunas = tiposRegras[tipo] || [];
                colunas.forEach(c => {
                    let val = $(this).find(`.${c.name}`).val();
                    if (!val || c.name === 'qtd_expr') return;
                    if (c.name === 'campo') {
                        condicoes['campo'] = val;
                    } else if (c.name === 'valor') {
                        condicoes['valor'] = isNaN(val) ? val : parseFloat(val);
                    } else if (c.name === 'tem_pintura') {
                        if (val !== '') {
                            condicoes['tem_pintura'] = val === 'true';
                        }
                    } else {
                        condicoes[c.name] = isNaN(val) ? val : parseFloat(val);
                    }
                });
                dados.push({condicoes, produto_id: produtoSelect.val(), desc_prod: produtoSelect.find('option:selected').text(), qtd_expr: qtd_expr});
            }
        });
        $('#id_expressao_json').val(JSON.stringify(dados, null, 2));
    }
    $('#id_tipo_regra').on('change', function () {
        const tipo = $(this).val();
        montarTabela(tipo);
        gerarJSON();
    });
    $('#add-linha').on('click', function () {
        const tipo = $('#id_tipo_regra').val();
        if (!tipo) {
            alert('Selecione o tipo primeiro');
            return;
        }
        const $linha = $(novaLinha(tipo));
        $('#tabela-regras tbody').append($linha);
        iniciarSelect2($linha);
    });
    $(document).on('input change', '.max, .valor, .campo, .produto, .qtd_expr, .tem_pintura', function () {gerarJSON();});
    $(document).on('click', '.remover', function () {
        $(this).closest('tr').remove();
        gerarJSON();
    });
    const tipoSistema = $('#id_tipo').val();
    if (tipoSistema === 'QTD') {
        $('#id_tipo_regra').val('qtd');
    }
    function carregarJSONReg() {
        let jsonText = $('#id_expressao_json').val();
        console.log("JSON RAW:", jsonText); // 👈 DEBUG
        if (!jsonText || jsonText.trim() === '') return;
        let dados;
        try {
            dados = typeof jsonText === 'string' ? JSON.parse(jsonText) : jsonText;
        } catch (e) {
            console.error('Erro ao fazer parse do JSON:', e);
            return;
        }
        if (!Array.isArray(dados)) return;
        let tipoSistema = $('#id_tipo').val();
        let tipo = $('#id_tipo_regra').val();
        // 🔥 FORÇA QTD
        if (tipoSistema === 'QTD') {
            tipo = 'qtd';
            $('#id_tipo_regra').val(tipo);
        }
        montarTabela(tipo);
        dados.forEach(item => {
            const $linha = $(novaLinha(tipo));
            $('#tabela-regras tbody').append($linha);
            // 🔹 Preenche condições (SELECAO)
            if (item.condicoes) {
                Object.keys(item.condicoes).forEach(key => {
                    let valor = item.condicoes[key];

                    // 🔥 CORREÇÃO PARA BOOLEAN
                    if (key === 'tem_pintura') {
                        valor = valor === true ? 'true' : 'false';
                    }

                    $linha.find(`.${key}`).val(valor).trigger('change');
                });
            }
            // 🔹 Preenche fórmula (QTD ou SELECAO)
            if (item.qtd_expr) {
                $linha.find('.qtd_expr').val(item.qtd_expr);
            }
            // 🔹 Inicializa select2
            iniciarSelect2($linha);
            // 🔹 Define produto
            setProduto($linha.find('.produto'), item.produto_id, item.desc_prod || `Produto ${item.produto_id}`);
        });
    }
    function setProduto($select, id, text) {
        let option = new Option(text, id, true, true);
        $select.append(option).trigger('change');
    }
    carregarJSONReg();
    // Teste
    $(document).on("click", '[id^="medidasBtn"]', function () {
        let id = $(this).attr("id").replace("medidasBtn", "");
        $("#medidas" + id).show();
        $("#clientes" + id).hide();
    });
    $(document).on("click", '[id^="clienteBtn"]', function () {
        let id = $(this).attr("id").replace("clienteBtn", "");
        $("#clientes" + id).show();
        $("#medidas" + id).hide();
    });
    $(document).on("shown.bs.modal", '[id^="infoEntModal"]', function () {
        let id = $(this).attr("id").replace("infoEntModal", "");
        $("#medidas" + id).show();
        $("#clientes" + id).hide();
    });
    // 🔹 Alterar labels conforme o tipo selecionado
    $('#tp-atrib').on('change', function () {
        if ($(this).val() === "0") {
            $('#lbl-campo-1').text("Margem (%)");
            $('#lbl-campo-2').text("Valor (R$)");
        } else if ($(this).val() === "1") {
            $('#lbl-campo-1').text("Valor (R$)");
            $('#lbl-campo-2').text("Margem (%)");
        }
    });
    // 🔹 Verificar checkboxes antes de abrir o modal
    $('#mdAttTbPreco').on('click', function (e) {
        const checkboxesMarcados = $('.task-checkbox:checked');
        if (checkboxesMarcados.length === 0) {
            e.preventDefault(); // impede o modal de abrir
            toast(`${ic_amarelo} Selecione ao menos um produto antes de continuar!`, cor_amarelo);
            return;
        }
        $('#attTbPrecModal').modal('show');
    });
    // Adição e Remoção de quantidade de Produto (Pedidos)
    $('.remQtdP').on('click', function () {
        let qtd = parseFloat($('#id_quantidadeP').val()) || 0;
        if (qtd > 0) $('#id_quantidadeP').val((qtd - 1).toFixed(2));
    });
    $('.addQtdP').on('click', function () {
        let qtd = parseFloat($('#id_quantidadeP').val()) || 0;
        $('#id_quantidadeP').val((qtd + 1).toFixed(2));
    });
    function gerarCorAleatoria() {
        const letras = '0123456789ABCDEF';
        let cor = '#';

        for (let i = 0; i < 6; i++) {
            cor += letras[Math.floor(Math.random() * 12)];
        }

        return cor;
    }

    function corTextoIdeal(hex) {
        hex = hex.replace('#', '');

        const r = parseInt(hex.substr(0, 2), 16);
        const g = parseInt(hex.substr(2, 2), 16);
        const b = parseInt(hex.substr(4, 2), 16);

        const brilho = (r * 299 + g * 587 + b * 114) / 1000;

        return brilho > 150 ? '#000' : '#FFF';
    }
    $('.badge-permissao').each(function () {

        const cor = gerarCorAleatoria();
        const corTexto = corTextoIdeal(cor);

        $(this).css({
            'background-color': cor,
            'color': corTexto,
            'border': 'none',
            'margin': '2px',
            'padding': '0px 6px',
            'border-radius': '10px',
            'display': 'inline-block'
        });

    });
    // VISUALIZAR ENTRADAS DE PRODUTO
    $('.ver-entradas').on('click', function() {
        const produtoId = $(this).data('produto-id');
        const modalEl = $(`#infoEntModal${produtoId}`)[0];
        const modal = new bootstrap.Modal(modalEl);
        const tableBody = $(`#entradasTableBody${produtoId}`);
        $.ajax({
            url: `/entradas/entradas-produto/${produtoId}/`, method: 'GET', dataType: 'json',
            success: function(response) {
                tableBody.empty(); // limpa o corpo da tabela
                if (response.entradas.length > 0) {
                    $.each(response.entradas, function(i, e) {
                        const row = `
                            <tr>
                                <td>${e.fornecedor}</td><td>${e.data}</td><td>${e.entrada_id}</td><td>${e.quantidade}</td><td>R$ ${e.valor_unitario.toFixed(2).replace('.', ',')}</td><td><strong>R$ ${e.total_entrada.toFixed(2).replace('.', ',')}</strong></td>
                            </tr>
                        `;
                        tableBody.append(row);
                    });
                } else {tableBody.append('<tr><td colspan="6" class="text-center">Nenhuma entrada encontrada.</td></tr>');}
                modal.show();
            }, error: function() {
                tableBody.html('<tr><td colspan="6" class="text-center text-danger">Erro ao carregar dados.</td></tr>');
                modal.show();
            }
        });
    });
    // NOVO TESTE
    $(function () {
        const seletorDatasGerais = '[id^="dt_pag_cr-"], #data_inicio1, #data_fim1, #id_data_vencimento, #dt_efet_ent, #inpDtPriParc, #id_dt_inicio, #data, #id_dt_emi, #id_dt_ent, #id_dt_venc, #id_data_certificado, #id_data_emissao, #id_data_emissao1, #id_data_entrega, #id_data_nascimento_administrador, #id_data_nascimento, #id_data_doc, #id_data_prop, #id_data_aniversario, #id_dt_visita, #id_px_visita, #dtVisita, #pxVisita';
        $(seletorDatasGerais).datepicker({
            changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy",  monthNamesShort: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], dayNamesMin: ["Do", "2ª", "3ª", "4ª", "5ª", "6ª", "Sá"]
        });
        $(seletorDatasGerais).each(function () {if (!$(this).val()) {$(this).val(obterDataAtual2());}});
    });
    // Usado quando o modal efetivarModal é aberto
    function limparBackdropsDuplicados() {
        const $backs = $('.modal-backdrop');
        if ($backs.length > 1) {$backs.not(':last').remove();}
        if ($('.modal.show').length) {$('body').addClass('modal-open');}
    }
    $(document).on('show.bs.modal', '[id^="efetivarModal-"]', function () {
        $('[id^="menuModal"]').modal('hide');
        setTimeout(() => {limparBackdropsDuplicados();}, 150);
    });
    $(document).on('hidden.bs.modal', '[id^="menuModal"]', function () {
        setTimeout(() => {limparBackdropsDuplicados();}, 150);
    });
    $(document).on('shown.bs.modal', '[id^="efetivarModal-"]', function () {
        const inpParc = $(this).find('#inpParc');
        const inpDiasPriParc = $(this).find('#inpDiasPriParc');
        const inpIntervalo = $(this).find('#inpIntervalo');
        const dtEfetivacao = $(this).find('#dt_efet_ent');
        const dtFatura = $(this).find('.dt-fat-orcamento');
        const inpDtPriParc = $(this).find('#inpDtPriParc');
        // Valores default
        if (!inpParc.val()) {inpParc.val(1);}
        if (!inpDiasPriParc.val()) {inpDiasPriParc.val(1);}
        if (!inpIntervalo.val()) {inpIntervalo.val(0);}
        if (!dtEfetivacao.val()) {dtEfetivacao.val(obterDataAtual2());}
        if (!dtFatura.val()) {dtFatura.val(obterDataAtual2());}
        if (dtEfetivacao.val()) {inpDtPriParc.val(addDtInterv(dtEfetivacao.val(), inpDiasPriParc.val()));}
        $('#dt_efet_ent, #inpDiasPriParc').on('change', function () {
            const dtEfetiv = $('#dt_efet_ent').val();
            const interv = $('#inpDiasPriParc').val();
            if (dtEfetiv && interv) {
                const nvDtPriParc = addDtInterv(dtEfetiv, interv);
                $('#inpDtPriParc').val(nvDtPriParc);
            }
        });
    });
    $(document).on('shown.bs.modal', '[id^="faturarModal-"]', function () {
        const dtFatura = $(this).find('.dt-fat-orcamento');
        // Valores default
        if (!dtFatura.val()) {dtFatura.val(obterDataAtual2());}
        $(document).on('click', '.btn-lib-dt-fat', function () {
            const dtFat = $('.dt-fat-orcamento');
            dtFat.prop('readonly', !dtFat.prop('readonly'));
        });
    });
    $(document).on('shown.bs.modal', '[id^="faturarModalP-"]', function () {
        limparBackdropsDuplicados();
        const dtFatura = $(this).find('.dt-fat-pedido');
        // Valores default
        if (!dtFatura.val()) {dtFatura.val(obterDataAtual2());}
        $(document).on('click', '.btn-lib-dt-fat', function () {
            const dtFat = $('.dt-fat-pedido');
            dtFat.prop('readonly', !dtFat.prop('readonly'));
        });
    });
    // Usado quando o modal informações de Pagamento é aberto
    function parseBR(valor) {
        if (!valor) return 0;

        valor = String(valor).trim();

        if (valor.includes(','))
            return Number(valor.replace(/\./g, '').replace(',', '.'));

        return Number(valor);
    }

    function parseEN(valor) {
        return Number(valor || 0);
    }
    function formatBR(valor) {
        return Number(valor || 0).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
    function formatarEN(valor) {
        const num = Number(valor || 0);
        return num.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
    function recalcularBaixa(modal, atualizarCampos = true) {
        const valorConta = parseBR(modal.find('[id^="valor_cr"]').val());
        const totalJurosOriginal = parseBR(modal.find('[id^="tot_juros_cr"]').val());
        const totalMultaOriginal = parseBR(modal.find('[id^="tot_multa_cr"]').val());
        const percDescJuros = parseFloat(modal.find('[id^="desc_j_cr"]').val()) || 0;
        const percDescMulta = parseFloat(modal.find('[id^="desc_m_cr"]').val()) || 0;
        const descontoJuros = totalJurosOriginal * (percDescJuros / 100);
        const descontoMulta = totalMultaOriginal * (percDescMulta / 100);
        const jurosFinal = Math.max(totalJurosOriginal - descontoJuros, 0);
        const multaFinal = Math.max(totalMultaOriginal - descontoMulta, 0);
        const descontoFinal = descontoJuros + descontoMulta;
        const totalPagar = valorConta + jurosFinal + multaFinal;
        if (atualizarCampos) {
            modal.find('[id^="juros_cr"]').val(formatBR(jurosFinal));
            modal.find('[id^="multa_cr"]').val(formatBR(multaFinal));
            modal.find('[id^="vl_tot_cr"]').val(formatBR(totalPagar));
            modal.find('[id^="vl_pg_cr"]').val(formatBR(totalPagar));
        }
        return { jurosFinal, multaFinal, descontoFinal, totalPagar };
    }
    function atualizarRestante(modal) {
        const total = parseBR(modal.find('[id^="vl_tot_cr"]').val());
        let soma = 0;
        modal.find('.vl-item-pgto').each(function () {soma += Number($(this).val());});
        const restante = total - soma;
        modal.find('[id^="restante_cr"]').text(formatBR(restante > 0 ? restante : 0));
        return restante;
    }
    $(document).on('shown.bs.modal', '[id^="mdInfoBaixa-"]', function () {
        const modal = $(this);
        const dtPagCr = modal.find('[id^="dt_pag_cr-"]');
        const contaId = modal.attr('id').split('-')[1];
        if (!dtPagCr.val()) {dtPagCr.val(obterDataAtual2());}
        modal.find('[id^="desc_j_cr"], [id^="desc_m_cr"]').off('input.baixa').on('input.baixa', function () {
            let valor = this.value.replace(/[^\d]/g, '');
            if (!valor) valor = '0';
            valor = (parseInt(valor, 10) / 100).toFixed(2);
            if (parseFloat(valor) > 100) {valor = '100.00';}
            this.value = valor;
            recalcularBaixa(modal);
            atualizarRestante(modal);
        });
        modal.find('[id^="btn_inc_forma"]').off('click.forma').on('click.forma', function () {
            const select = modal.find('[id^="formas_pgto_cr"]');
            const valorInput = modal.find('[id^="vl_pg_cr"]');
            const tbody = modal.find(`#tb_formas_${contaId} tbody`);
            const formaId = select.val();
            const formaTxt = select.find('option:selected').text();
            const valor = parseBR(valorInput.val());
            const restante = atualizarRestante(modal);
            if (!formaId) return toast('Selecione uma forma!', cor_amarelo);
            if (valor <= 0) return toast('Valor inválido!', cor_amarelo);
            if (valor > restante) return toast('Valor maior que restante!', cor_amarelo);
            const gateway = select.data('gateway') || 'nenhum';
            const credencial = JSON.stringify(select.data('credencial') || {});
            tbody.append(`
                <tr data-gateway="${gateway}" data-credencial='${credencial}'>
                    <td>${formaTxt}<input type="hidden" name="forma_id[]" value="${formaId}"></td>
                    <td class="text-end">
                        ${formatBR(valor)}
                        <input type="hidden" class="vl-item-pgto" name="forma_valor[]" value="${valor.toFixed(2)}">
                    </td>
                    <td class="text-center">
                        <button type="button" class="btn btn-danger btn-sm remover-forma">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `);
            const novoRestante = atualizarRestante(modal);
            valorInput.val(formatBR(novoRestante > 0 ? novoRestante : 0));
            select.val(null).trigger('change');
        });
        modal.off('click.removerForma').on('click.removerForma', '.remover-forma', function () {
            $(this).closest('tr').remove();
            const restante = atualizarRestante(modal);
            modal.find('[id^="vl_pg_cr"]').val(formatBR(restante > 0 ? restante : 0));
        });
        function iniciarBaixaConta(modal) {
            recalcularBaixa(modal);
            atualizarRestante(modal);
        }
        modal.find('[id^="formas_pgto_cr"]').off('change.forma').on('change.forma', function () {
            const $select = $(this);
            const formaId = $select.val();
            if (!formaId) return;
            $.get('/formas_pgto/forma-pgto-info/' + formaId + '/', function (data) {
                $select.data('gateway', data.gateway || 'nenhum');
                $select.data('credencial', data.credenciais || null);
            });
        });
        modal.find('.btn-baixar-cr').off('click.baixar').on('click.baixar', function () {
            const linhas = modal.find(`#tb_formas_${contaId} tbody tr`);
            let temGateway = false;
            linhas.each(function () {
                const gateway = ($(this).data('gateway') || '').toLowerCase();
                if (gateway && gateway !== 'nenhum') {
                    temGateway = true;
                    return false;
                }
            });
            if (temGateway) {
                const formas = [];
                linhas.each(function () {
                    const formaId = $(this).find('input[name="forma_id[]"]').val();
                    const valor = $(this).find('input[name="forma_valor[]"]').val();
                    if (formaId && valor) {
                        formas.push({
                            forma_id: formaId,
                            valor: valor
                        });
                    }
                });
                iniciarLoading();
                $.ajax({
                    url: `/contas_receber/${contaId}/gerar-pagamento/`,
                    method: 'POST',
                    data: {
                        formas: JSON.stringify(formas),
                        csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
                    },
                    success: function (resp) {
                        if (resp.erro) {
                            toast(resp.erro, cor_vermelho);
                            return;
                        }
                        fecharLoading();
                        abrirModalPixConta(contaId, resp);
                    }
                });
                return; // 🚫 BLOQUEIA BAIXA NORMAL
            }
            const calc = recalcularBaixa(modal);
            const form = $('<form>', {
                method: 'POST',
                action: `/contas_receber/pagar/${contaId}/`
            });
            form.append(`<input type="hidden" name="csrfmiddlewaretoken" value="${$('[name=csrfmiddlewaretoken]').val()}">`);
            form.append(`<input type="hidden" name="juros" value="${formatarEN(calc.jurosFinal)}">`);
            form.append(`<input type="hidden" name="multa" value="${formatarEN(calc.multaFinal)}">`);
            form.append(`<input type="hidden" name="desconto" value="${formatarEN(calc.descontoFinal)}">`);
            modal.find('input[name="forma_id[]"], input[name="forma_valor[]"]').each(function () {
                form.append($(this).clone());
            });
            $('body').append(form);
            form.submit();
        });
        // 🔥 BAIXA NORMAL
        function baixarContaNormal(modal, contaId, formas) {
            const calc = recalcularBaixa(modal, false);
            const form = $('<form>', {
                method: 'POST',
                action: `/contas_receber/pagar/${contaId}/`
            });
            form.append(`<input type="hidden" name="csrfmiddlewaretoken" value="${$('input[name=csrfmiddlewaretoken]').val()}">`);
            form.append(`<input type="hidden" name="juros" value="${calc.jurosFinal}">`);
            form.append(`<input type="hidden" name="multa" value="${calc.multaFinal}">`);
            form.append(`<input type="hidden" name="desconto" value="${calc.descontoFinal}">`);
            formas.forEach(f => {
                form.append(`<input type="hidden" name="forma_id[]" value="${f.forma}">`);
                form.append(`<input type="hidden" name="forma_valor[]" value="${f.valor}">`);
            });
            $('body').append(form);
            form.submit();
        }
        // 🔥 GERAR PIX
        function gerarPixConta(contaId, formas) {
            iniciarLoading();
            $.post(`/contas_receber/${contaId}/gerar-pagamento/`, {
                csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(),
                formas: JSON.stringify(formas)
            }, function (resp) {
                fecharLoading();
                if (resp.qr_code) {
                    abrirModalPixConta(contaId, resp);
                } else {
                    alert('Erro ao gerar PIX');
                }
            });
        }
        function abrirModalPixConta(contaId, resp) {
            $('#pixQrContainer').html('');
            $('#statusPix').removeClass('d-none');
            $('#statusSucesso').addClass('d-none');
            $('#pixQrContainer').html(`
                <div class="mb-3">
                    <img src="data:image/png;base64,${resp.qr_base64}" width="220" class="mb-2">
                    <div class="input-group">
                        <input type="text"
                               class="form-control text-center"
                               value="${resp.qr_code}"
                               readonly>
                        <button class="btn btn-outline-secondary btn-copiar"
                                data-code="${resp.qr_code}">
                            Copiar
                        </button>
                    </div>
                    <strong class="d-block mt-2">
                        R$ ${formatBR(resp.valor)}
                    </strong>
                </div>
            `);
            $(document).off('click.copiarPix').on('click.copiarPix', '.btn-copiar', function () {
                navigator.clipboard.writeText($(this).data('code'));
                toast('Código PIX copiado!', cor_verde);
            });
            const modalPix = new bootstrap.Modal(document.getElementById('modalPixPagamento'));
            modalPix.show();
            const interval = setInterval(() => {
                $.get(`/contas_receber/${contaId}/status-pagamento/`, function (resp) {
                    if (resp.pago) {
                        clearInterval(interval);
                        let mensagem = 'Conta recebida com sucesso!';
                        if (resp.parcial) {
                            mensagem = `Baixa parcial realizada. Saldo restante: R$ ${formatBR(resp.restante)}`;
                        }
                        $('#modalPixPagamento .modal-body').html(`
                            <div class="text-center py-4">
                                <div class="check-circle mx-auto">
                                    <i class="fa-solid fa-check"></i>
                                </div>
                                <h5 class="text-success fw-bold">Pagamento confirmado!</h5>
                                <p class="text-muted mb-0">Finalizando baixa...</p>
                            </div>
                        `);
                        toast(`${ic_verde} ${mensagem}`, cor_verde);
                        setTimeout(() => {
                            modalPix.hide();
                            iniciarLoading();
                            setTimeout(() => {
                                window.location.href = `/contas_receber/lista/?s=${contaId}`;
                            }, 3000);
                        }, 2000);
                    }
                });
            }, 3000);
            document.getElementById('modalPixPagamento')
                .addEventListener('hidden.bs.modal', () => clearInterval(interval), { once: true });
        }
        recalcularBaixa(modal);
        const restante = atualizarRestante(modal);
        modal.find('[id^="vl_pg_cr"]').val(formatBR(restante > 0 ? restante : 0));
    });
    document.addEventListener('focusin', function (e) {if (e.target.closest('.select2-container') || e.target.closest('.ui-datepicker')) {e.stopPropagation();}}, true);
    $(document).on('shown.bs.modal', '#mdResOrc', function () {
        const modal = $(this);
        const dtInicio = modal.find('#data_inicio2');
        const dtFim = modal.find('#data_fim2');
        const hoje = obterDataAtual2();
        if (!dtInicio.val()) dtInicio.val(hoje);
        if (!dtFim.val()) dtFim.val(hoje);
        if (dtInicio.hasClass('hasDatepicker')) dtInicio.datepicker('destroy');
        if (dtFim.hasClass('hasDatepicker')) dtFim.datepicker('destroy');
        dtInicio.datepicker({
            changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy",  monthNamesShort: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], dayNamesMin: ["Do", "2ª", "3ª", "4ª", "5ª", "6ª", "Sá"],
            beforeShow: function () {setTimeout(function () {$('.ui-datepicker').css('z-index', 2000);}, 0);}
        });
        dtFim.datepicker({
            changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy",  monthNamesShort: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], dayNamesMin: ["Do", "2ª", "3ª", "4ª", "5ª", "6ª", "Sá"],
            beforeShow: function () {setTimeout(function () {$('.ui-datepicker').css('z-index', 2000);}, 0);}
        });
    });
    //
    $('#id_desconto').on("blur", function() {
        let valor = $(this).val().replace(',', '.').trim();
        if (valor === "" || isNaN(valor)) {$(this).val("0.00");}
        else {$(this).val(parseFloat(valor).toFixed(2));}
    });
    $(document).on("click", ".editable#total-frete", function () {
        const $span = $(this);
        const valor = $span.text().trim();
        const $input = $(`<input type="text" id="total-frete" style="float: right;" class="form-control d-inline-block w-auto inpFrete text-end fw-bold" value="${valor}">`);
        $span.replaceWith($input);
        $input.focus().select();
        $input.on("input", function() {
            let val = $(this).val().replace(/[^0-9]/g, ""); // mantém só números
            if (val === "") {
                $(this).val("0.00");
                return;
            }
            let num = (parseFloat(val) / 100).toFixed(2);
            $(this).val(num);
        });
        $input.on("blur keydown", function(e) {
            if (e.type === "blur" || (e.type === "keydown" && e.key === "Enter")) {
                e.preventDefault();
                const novoValorRaw = $input.val().trim();
                if (novoValorRaw === "") {
                    alert("Campo (Frete) é obrigatório!");
                    $input.focus();
                    return;
                }
                const novoValorNum = parseFloat(novoValorRaw.replace(',', '.')) || 0;
                const $newSpan = $(`
                    <span class="editable" id="total-frete" style="background-color: #F08080; color: white; border-radius: 15px; padding-left: 10px; padding-right: 10px; float: right;">
                        ${novoValorNum.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                `);
                $input.replaceWith($newSpan);
                $('#id_frete').val(novoValorNum.toFixed(2));
                calcTotalEntrada();
            }
        });
    });
    var produtos = 0;
    var desconto = 0;
    var frete = 0;
    var total = 0;
    function calcTotalEntrada() {
        produtos = 0;
        desconto = 0;
        frete = 0;
        total = 0;
        $('#tabela-produtos tbody tr').each(function() {
            let vlProdTxt = $(this).find('td:nth-child(7)').text().trim().replace(',', '.');
            let vlProdNb = parseFloat(vlProdTxt);
            if (!isNaN(vlProdNb)) {produtos += vlProdNb;}
            let vlDsctTxt = $(this).find('td:nth-child(6)').text().trim().replace(',', '.');
            let vlDsctNb = parseFloat(vlDsctTxt);
            if (!isNaN(vlDsctNb)) {desconto += vlDsctNb;}
        });
        let freteTxt = $('#total-frete').is('input') ? $('#total-frete').val() : $('#total-frete').text();
        frete = parseFloat(freteTxt.replace(',', '.')) || 0;
        total = produtos + frete;
        $('#total-produtos').text('R$ ' + produtos.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#total-desconto').text('R$ ' + desconto.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#total-frete').text(frete.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#id_frete').val(Number(frete).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#valor-total').text('R$ ' + total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    }
    // Pedidos
    var produtosP = 0;
    var descontoP = 0;
    var freteP = 0;
    var totalP = 0;
    function calcTotalPedido() {
        produtosP = 0;   // total bruto (sem desconto)
        descontoP = 0;   // total de descontos (positivo)
        freteP    = 0;
        totalP    = 0;

        $('#tabela-produtos tbody tr').each(function() {

            // 🔹 DADOS BASE
            let preco = $(this).find('input[name*="[preco_unitario]"]').val();
            let qtd   = $(this).find('input[name*="[quantidade]"]').val();

            let precoNum = parseFloat(String(preco).replace(',', '.')) || 0;
            let qtdNum   = parseFloat(String(qtd).replace(',', '.')) || 0;

            // 🔹 TOTAL BRUTO DO ITEM (sem desconto)
            let totalBrutoItem = precoNum * qtdNum;
            produtosP += totalBrutoItem;

            // 🔹 DESCONTO / ACRÉSCIMO EM REAIS (já calculado antes)
            let descReal = $(this).find('input[name*="[valor_desc_real]"]').val();
            let operacao = ($(this).find('input[name*="[operacao]"]').val() || '').toLowerCase();

            let descNum = parseFloat(String(descReal).replace(',', '.')) || 0;

            if (operacao === "desconto") {
                descontoP += descNum;   // soma desconto
            } else {
                descontoP -= descNum;   // acréscimo reduz o "desconto"
            }
        });

        // 🔹 FRETE
        let freteTxt = $('#total-frete').is('input')
            ? $('#total-frete').val()
            : $('#total-frete').text();

        freteP = parseFloat(String(freteTxt).replace(',', '.')) || 0;

        // 🔹 TOTAL FINAL
        totalP = produtosP - descontoP + freteP;

        // 🔹 FORMATAÇÃO (pode trocar para pt-BR se quiser)
        $('#total-produtos').text('R$ ' + produtosP.toFixed(2));
        $('#total-desconto').text('R$ ' + descontoP.toFixed(2));
        $('#total-frete').text(freteP.toFixed(2));
        $('#id_frete').val(freteP.toFixed(2));
        $('#valor-total').text('R$ ' + totalP.toFixed(2));
    }
    // Entrada de Pedidos
    $('#id_tipo').on('change', function () {
        const tipoEnt = $(this).val();
        if (tipoEnt === 'Pedido') {$("#id_modelo, #id_serie, #id_nat_op, #id_chave_acesso").prop("disabled", true);}
        else if (tipoEnt === "Nota Fiscal") {$("#id_modelo, #id_serie, #id_nat_op, #id_chave_acesso").prop("disabled", false);}
    });
    let ident = 0;
    $("#add-cod-sec-tab").click(function () {
        let cod = $('#cod-sec').val();
        if (cod === "") {toast(`${ic_amarelo} Código deve ser informado!`, cor_amarelo);}
        else {
            let idx = ident++;
            let codigoJaExiste = false;
            $("#tb-cod-sec tbody input[name*='[codigo]']").each(function() {
                if ($(this).val() === cod) {
                    codigoJaExiste = true;
                    return false; // sai do each
                }
            });
            if (codigoJaExiste) {toast(`${ic_amarelo} O código "${cod}" já está incluso na listagem!`, cor_amarelo);}
            else {
                $("#tb-cod-sec tbody").append(`
                    <tr data-id="${idx}">
                        <td>${cod}<input type="hidden" name="codigo[${idx}][codigo]" value="${cod}"></td>
                        <td><button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button></td>
                    </tr>
                `);
            }
        }
        $("#cod-sec").val("");
        $("#cod-sec").focus();
    });
    $('#cod-sec').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault(); // evita o submit do form
            $("#add-cod-sec-tab").click(); // aciona o mesmo evento do botão
        }
    });
    let trEdit = null;          // variável global para edição
    let identificador = $("#tab-prec tbody tr").length; // contador inicial
    let editing = false;        // flag para evitar sobrescrever margem ao editar
    let bloqueio = false;       // evita loop de eventos
    $('#id_vl_tab').on('blur', function () {
        if (bloqueio) return;
        bloqueio = true;
        const valorCompra = parseFloat($('#id_vl_compra').val()) || 0;
        const valorProduto = parseFloat($(this).val()) || 0;
        if (valorCompra > 0 && valorProduto > 0) {
            const margem = ((valorProduto - valorCompra) / valorCompra) * 100;
            $('#id_margem').val(margem < 0 ? '0.00' : margem.toFixed(2));
        }
        else {$('#id_margem').val('0.00');}
        bloqueio = false;
    });
    // Recalcular VALOR PRODUTO ao editar MARGEM
    $('#id_margem').on('blur', function () {
        if (bloqueio) return;
        bloqueio = true;
        const valorCompra = parseFloat($('#id_vl_compra').val()) || 0;
        const margem = parseFloat($(this).val()) || 0;
        if (valorCompra > 0) {
            const valorProduto = valorCompra * (1 + margem / 100);
            $('#id_vl_tab').val(valorProduto.toFixed(2));
        }
        bloqueio = false;
    });
    // Recalcular VALOR PRODUTO ao editar VALOR COMPRA
    $('#id_vl_compra').on('blur', function () {
        if (bloqueio) return;
        bloqueio = true;
        const valorCompra = parseFloat($(this).val()) || 0;
        const margem = parseFloat($('#id_margem').val()) || 0;
        if (valorCompra > 0 && margem !== 0) {
            const valorProduto = valorCompra * (1 + margem / 100);
            $('#id_vl_tab').val(valorProduto.toFixed(2));
        }
        bloqueio = false;
    });
    // ======= CHANGE DA TABELA =======
    $('#id_tabela').on('change', function () {
        if (editing) return; // ignora quando estiver editando
        const tp_atrib = $('#tp-atrib').val();
        const idTabela = $(this).val();
        const precoCompra = parseFloat($('#id_vl_compra').val()) || 0;
        if (!idTabela) return;
        $.ajax({
            url: "/tabelas_preco/get/", method: "GET", data: { id: idTabela },
            success: function(response) {
                if (response.margem !== undefined) {
                    $('#id_margem').val(response.margem);
                    if (tp_atrib === "0") {
                        $('#campo_1').val(response.margem);}
                    let calc = precoCompra * (1 + response.margem / 100);
                    $('#id_vl_tab').val(calc.toFixed(2));
                }
            }, error: function() {toast(`${ic_vermelho} Erro ao buscar a tabela de preço!`, cor_vermelho);}
        });
    });
    $('#tb-prec').on('change', function () {
        if (editing) return; // ignora quando estiver editando
        const tp_atrib = $('#tp-atrib').val();
        const idTabela = $(this).val();
        const precoCompra = parseFloat($('#id_vl_compra').val()) || 0;
        if (!idTabela) return;
        $.ajax({
            url: "/tabelas_preco/get/", method: "GET", data: { id: idTabela },
            success: function(response) {
                if (response.margem !== undefined) {
                    if (tp_atrib === "0") {$('#campo_1').val(response.margem);}
                    let calc = precoCompra * (1 + response.margem / 100);
                    $('#id_vl_tab').val(calc.toFixed(2));
                }
            }, error: function() {toast(`${ic_vermelho} Erro ao buscar a tabela de preço!`, cor_vermelho);}
        });
    });
    let bloqueioEnt = false;
    let editingTabEnt = false;
    $('#id_vl_tabEnt').on('blur', function () {
        if (bloqueioEnt) return;
        bloqueioEnt = true;
        const precoUnit = parseFloat(String($('#id_preco_unit').val()).replace(',', '.')) || 0;
        const valorVenda = parseFloat(String($(this).val()).replace(',', '.')) || 0;
        if (precoUnit > 0 && valorVenda > 0) {
            const margem = ((valorVenda - precoUnit) / precoUnit) * 100;
            $('#id_margem').val(margem < 0 ? '0.00' : margem.toFixed(2));
        }
        else {$('#id_margem').val('0.00');}
        bloqueioEnt = false;
    });
    $('#id_margem').on('blur', function () {
        if (bloqueioEnt) return;
        bloqueioEnt = true;
        const precoUnit = parseFloat(String($('#id_preco_unit').val()).replace(',', '.')) || 0;
        const margem = parseFloat(String($(this).val()).replace(',', '.')) || 0;
        if (precoUnit > 0) {
            const valorVenda = precoUnit * (1 + margem / 100);
            $('#id_vl_tabEnt').val(valorVenda.toFixed(2));
        }
        else {$('#id_vl_tabEnt').val('0.00');}
        bloqueioEnt = false;
    });
    $('#id_preco_unit').on('blur', function () {
        if (bloqueioEnt) return;
        bloqueioEnt = true;
        const precoUnit = parseFloat(String($(this).val()).replace(',', '.')) || 0;
        const margem = parseFloat(String($('#id_margem').val()).replace(',', '.')) || 0;
        if (precoUnit > 0) {
            const valorVenda = precoUnit * (1 + margem / 100);
            $('#id_vl_tabEnt').val(valorVenda.toFixed(2));
        }
        else {$('#id_vl_tabEnt').val('0.00');}
        bloqueioEnt = false;
    });
    $('#id_tabelaEnt').on('change', function () {
        if (editingTabEnt) return;
        const idTabela = $(this).val();
        const precoUnit = parseFloat(String($('#id_preco_unit').val()).replace(',', '.')) || 0;
        if (!idTabela) return;
        $.ajax({
            url: "/tabelas_preco/get/", method: "GET", data: { id: idTabela }, success: function (response) {
                if (response.margem !== undefined) {
                    const margem = parseFloat(response.margem) || 0;
                    $('#id_margem').val(margem.toFixed(2));
                    const valorVenda = precoUnit * (1 + margem / 100);
                    $('#id_vl_tabEnt').val(valorVenda.toFixed(2));
                }
            },
            error: function () {toast(`${ic_vermelho} Erro ao buscar a tabela de preço!`, cor_vermelho);}
        });
    });
    // ======= ADD / EDIT / REMOVE =======
    $('#add-tab').css('background-color', '').html('<i class="fa-solid fa-plus"></i> Incluir');
    function resetInputsTab() {
        $("#id_vl_tab, #id_vl_tabEnt, #id_margem").val("0.00");
        $('#id_tabelaEnt').val(null);
        $("#id_tabelaEnt").focus();
    }
    // Clique no botão para adicionar ou salvar
    $("#add-tab").click(function () {
        let tabId = $('#id_tabela').val();
        let tabNome = $('#id_tabela option:selected').text();
        let mrg = $("#id_margem").val();
        let vl_p = $("#id_vl_tab").val();
        if (!tabId) {
            toast(`${ic_amarelo} Selecione uma tabela antes de adicionar!`, cor_amarelo);
            return;
        }
        if (vl_p === "0.00" || vl_p === "" || vl_p === "0") {
            toast(`${ic_amarelo} Preço de Venda deve ser informado!`, cor_amarelo);
            return;
        }
        if (trEdit) {
            let idx = trEdit.data("id");
            trEdit.find("td:eq(0)").html(`${tabNome}<input type="hidden" name="tab_preco[${idx}][tabela]" value="${tabId}">`);
            trEdit.find("td:eq(1)").html(`${mrg}<input type="hidden" name="tab_preco[${idx}][margem]" value="${mrg}">`);
            trEdit.find("td:eq(2)").html(`${vl_p}<input type="hidden" name="tab_preco[${idx}][vl_prod]" value="${vl_p}">`);
            trEdit = null;
            $("#id_tabela").prop("disabled", false);
            $('#add-tab').css('background-color', '').html('<i class="fa-solid fa-plus"></i> Incluir');
        } else {
            let idx = identificador++;
            $("#tab-prec tbody tr.vazio").remove();
            let tabelaJaExiste = false;
            $("#tab-prec tbody input[name*='[tabela]']").each(function() {
                if ($(this).val() === tabId) {
                    tabelaJaExiste = true;
                    return false;
                }
            });
            if (tabelaJaExiste) {toast(`${ic_amarelo} Tabela "${tabNome}" já está inclusa na listagem!`, cor_amarelo);}
            else {
                $("#tab-prec tbody").append(`
                    <tr data-id="${idx}">
                        <td>${tabNome}<input type="hidden" name="tab_preco[${idx}][tabela]" value="${tabId}"></td>
                        <td>${mrg}<input type="hidden" name="tab_preco[${idx}][margem]" value="${mrg}"></td>
                        <td>${vl_p}<input type="hidden" name="tab_preco[${idx}][vl_prod]" value="${vl_p}"></td>
                        <td>
                            <button type="button" class="editando btn btn-success btn-sm mt-1 mb-1"><i class="fa-solid fa-pen-to-square"></i></button>
                            <button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>
                `);
            }
        }
        resetInputsTab();
    });
    // ======= REMOVER LINHA =======
    $(document).on("click", ".remover", function () {$(this).closest("tr").remove();});
    // ======= EDITAR LINHA =======
    $(document).on("click", ".editando", function () {
        trEdit = $(this).closest("tr");
        const idx = trEdit.data("id");
        const tabId = trEdit.find(`input[name="tab_preco[${idx}][tabela]"]`).val();
        const mrg = trEdit.find(`input[name="tab_preco[${idx}][margem]"]`).val();
        const vl_p = trEdit.find(`input[name="tab_preco[${idx}][vl_prod]"]`).val();
        editing = true; // ativa flag
        const select = $("#id_tabela");
        if (select.find(`option[value='${tabId}']`).length === 0) {
            const tabText = trEdit.find("td:eq(0)").text().trim();
            select.append(`<option value="${tabId}">${tabText}</option>`);
        }
        $("#id_margem").val(mrg);
        $("#id_vl_tab").val(vl_p);
        select.val(tabId);
        select.prop("disabled", true);
        select.trigger('change');
        $("#id_vl_tab").focus();
        $('#add-tab').css('background-color', 'gray').html('<i class="fa-solid fa-floppy-disk"></i> Salvar');
        editing = false; // desativa flag
    });
    // ENTRADAS DE PEDIDOS / NF
    let contador = 0;
    let trEditando = null;
    async function buscarDadosProduto(cod) {
        const resp = await $.ajax({url: "/produtos/lista_ajax_ent/", type: "GET", data: { s: cod, tp: "cod" }, dataType: "json"});
        if (!resp.produtos || !resp.produtos.length) {throw new Error("Produto não encontrado.");}
        return resp.produtos[0];
    }
    let tabelasEntTmp = [];
    let trEditTabEnt = null;
    function renderTabelasEntModal() {
        const $tbody = $("#tab-prec tbody");
        $tbody.empty();
        if (tabelasEntTmp.length === 0) {
            $tbody.append(`
                <tr class="vazio"><td colspan="4" class="text-center">Nenhuma tabela inserida.</td></tr>
            `);
            return;
        }
        tabelasEntTmp.forEach((item, i) => {
            let valorFmt = parseFloat(String(item.valor || 0).replace(",", ".")).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            let margemFmt = parseFloat(String(item.margem || 0).replace(",", ".")).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            $tbody.append(`
                <tr data-idx="${i}">
                    <td>${item.tabela_nome}</td>
                    <td>${margemFmt}<input type="hidden" value="${item.margem}"></td>
                    <td>${valorFmt}<input type="hidden" value="${item.valor}"></td>
                    <td>
                        <button type="button" class="editar-tab-ent btn btn-success btn-sm mt-1 mb-1"><i class="fa-solid fa-pen-to-square"></i></button>
                        <button type="button" class="remover-tab-ent btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `);
        });
    }
    function resetBtnTabEnt() {
        $("#add-tabEnt").html('<i class="fa-solid fa-plus"></i> Incluir').removeAttr("style").removeClass("btn-secondary btn-warning btn-success").addClass("btn-dark").css("margin-top", "30px");
        $("#id_tabelaEnt").prop("disabled", false).val(null).trigger("change");
        $("#id_margem").val("0.00");
        $("#id_vl_tabEnt").val("0.00");
    }
    $("#add-tabEnt").click(function () {
        let tabId = $('#id_tabelaEnt').val();
        let tabNome = $('#id_tabelaEnt option:selected').text().trim();
        let mrg = ($("#id_margem").val() || "0").replace(",", ".");
        let vl_p = ($("#id_vl_tabEnt").val() || "0").replace(",", ".");
        if (!tabId) {
            toast(`${ic_amarelo} Selecione uma tabela antes de adicionar!`, cor_amarelo);
            return;
        }
        if (vl_p === "0.00" || vl_p === "" || vl_p === "0") {
            toast(`${ic_amarelo} Preço de Venda deve ser informado!`, cor_amarelo);
            return;
        }
        if (trEditTabEnt !== null) {
            tabelasEntTmp[trEditTabEnt] = {tabela_id: tabId, tabela_nome: tabNome, margem: parseFloat(mrg || 0).toFixed(2), valor: parseFloat(vl_p || 0).toFixed(2)};
            trEditTabEnt = null;
        } else {
            let tabelaJaExiste = tabelasEntTmp.some(t => String(t.tabela_id) === String(tabId));
            if (tabelaJaExiste) {
                toast(`${ic_amarelo} Tabela "${tabNome}" já está inclusa na listagem!`, cor_amarelo);
                return;
            }
            tabelasEntTmp.push({tabela_id: tabId, tabela_nome: tabNome, margem: parseFloat(mrg || 0).toFixed(2), valor: parseFloat(vl_p || 0).toFixed(2)});
        }
        renderTabelasEntModal();
        resetBtnTabEnt();
    });
    $('#add-produtos').on('click', function() {
        $("#add-tabEnt").html('<i class="fa-solid fa-plus"></i> Incluir').addClass("btn-dark");
        $('#edProdModal').modal('show');
    });
    $(document).on("click", ".editar-tab-ent", function () {
        let idx = $(this).closest("tr").data("idx");
        let item = tabelasEntTmp[idx];
        trEditTabEnt = idx;
        const select = $("#id_tabelaEnt");
        if (select.find(`option[value='${item.tabela_id}']`).length === 0) {select.append(`<option value="${item.tabela_id}">${item.tabela_nome}</option>`);}
        select.val(item.tabela_id);
        $("#id_margem").val(item.margem);
        $("#id_vl_tabEnt").val(item.valor);
        select.prop("disabled", true);
        $('#add-tabEnt').css('background-color', 'gray').html('<i class="fa-solid fa-floppy-disk"></i> Salvar');
    });
    $(document).on("click", ".remover-tab-ent", function () {
        let idx = $(this).closest("tr").data("idx");
        tabelasEntTmp.splice(idx, 1);
        if (trEditTabEnt === idx) trEditTabEnt = null;
        renderTabelasEntModal();
    });
    function montarResumoTabelasEnt(tabelas) {
        let html = `<div class="col-tabelas-wrap">`;
        tabelas.forEach(t => {
            let nome = (t.tabela_nome || "").toUpperCase();
            let valor = parseFloat(String(t.valor || 0).replace(",", ".")).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            html += `
                <div class="linha-tabela-pill">
                    <span class="tp-nome">${nome}</span>
                    <span class="tp-valor">${valor}</span>
                </div>
            `;
        });
        html += `</div>`;
        return html;
    }
    function montarInputsTabelasEnt(idx, tabelas) {
        if (!tabelas || tabelas.length === 0) return "";
        let html = "";
        tabelas.forEach((t, i) => {
            html += `
                <input type="hidden" name="produtos[${idx}][tabelas][${i}][tabela_id]" value="${t.tabela_id}">
                <input type="hidden" name="produtos[${idx}][tabelas][${i}][tabela_nome]" value="${t.tabela_nome}">
                <input type="hidden" name="produtos[${idx}][tabelas][${i}][margem]" value="${t.margem}">
                <input type="hidden" name="produtos[${idx}][tabelas][${i}][valor]" value="${t.valor}">
            `;
        });
        return html;
    }
    function carregarTabelasEntDaLinha(idx, $tr) {
        let tabelas = [];
        $tr.find(`input[name^="produtos[${idx}][tabelas]"]`).each(function () {
            let name = $(this).attr("name");
            let val = $(this).val();
            let match = name.match(/produtos\[\d+\]\[tabelas\]\[(\d+)\]\[(.+)\]/);
            if (!match) return;
            let i = parseInt(match[1], 10);
            let campo = match[2];
            if (!tabelas[i]) tabelas[i] = {};
            tabelas[i][campo] = val;
        });
        return tabelas.filter(Boolean);
    }
    // Adicionando um produto na lista de Entrada.
    $("#add-produto-lista").click(async function () {
        let cod = $('#id_cod_produto').val();
        let prod = $("#id_desc_prod").val();
        let qtd = $("#id_quantidade").val();
        let preco = $("#id_preco_unit").val();
        let dsct = $("#id_desconto").val();
        let qtdNum = parseFloat(String(qtd).replace(",", ".")) || 0;
        let precoNum = parseFloat(String(preco).replace(",", ".")) || 0;
        let dsctNum = parseFloat(String(dsct).replace(",", ".")) || 0;
        let total = ((precoNum * qtdNum) - dsctNum).toFixed(2);
        if (!cod) {
            toast(`${ic_amarelo} Informe o código do produto!`, cor_amarelo);
            return;
        }
        if (precoNum <= 0) {
            toast(`${ic_amarelo} Preço Unitário deve ser informado!`, cor_amarelo);
            return;
        }
        if (qtdNum <= 0) {
            toast(`${ic_amarelo} Quantidade deve ser informada!`, cor_amarelo);
            return;
        }
        try {
            await salvarTabelasProdutoAjax(cod, tabelasEntTmp);
        } catch (xhr) {
            let msg = xhr.responseJSON?.msg || "Erro ao salvar tabelas no produto.";
            toast(`${ic_vermelho} ${msg}`, cor_vermelho);
            return;
        }
        let resumoTabelas = montarResumoTabelasEnt(tabelasEntTmp);
        if (trEditando) {
            let idx = trEditando.data("id");
            trEditando.find("td:eq(1)").html(`${cod}<input type="hidden" name="produtos[${idx}][codigo]" value="${cod}">`);
            trEditando.find("td:eq(2)").html(`${prod}<input type="hidden" name="produtos[${idx}][produto]" value="${prod}">`);
            trEditando.find("td:eq(3)").html(`${qtd}<input type="hidden" name="produtos[${idx}][quantidade]" value="${qtd}">`);
            trEditando.find("td:eq(4)").html(`${preco}<input type="hidden" name="produtos[${idx}][preco_unitario]" value="${preco}">`);
            trEditando.find("td:eq(5)").html(`${dsct}<input type="hidden" name="produtos[${idx}][desconto]" value="${dsct}">`);
            trEditando.find("td:eq(6)").text(total);
            trEditando.find("td:eq(7)").html(`${resumoTabelas}${montarInputsTabelasEnt(idx, tabelasEntTmp)}`);
            trEditando.find(".task-checkbox").prop('checked', false);
            $("#select-all").prop('checked', false);
            trEditando = null;
        } else {
            let idx = contador++;
            $("#tabela-produtos tbody tr.vazio").remove();
            let codigoJaExiste = false;
            $("#tabela-produtos tbody input[name*='[codigo]']").each(function() {
                if ($(this).val() === cod) {
                    codigoJaExiste = true;
                    return false;
                }
            });
            if (codigoJaExiste) {
                toast(`${ic_amarelo} O código "${cod}" já está incluso na listagem!`, cor_amarelo);
                return;
            }
            $("#tabela-produtos tbody").append(`
                <tr data-id="${idx}">
                    <td style="text-align: center; padding-top: 8px; cursor: pointer;" onclick="toggleTaskCheckbox(this)">
                        <input type="checkbox" class="form-check-input task-checkbox" name="multi" value="${cod}" onclick="event.stopPropagation(); checkIfAllSelected(); updateMassChangesButton();">
                    </td>
                    <td>${cod}<input type="hidden" name="produtos[${idx}][codigo]" value="${cod}"></td>
                    <td>${prod}<input type="hidden" name="produtos[${idx}][produto]" value="${prod}"></td>
                    <td>${qtd}<input type="hidden" name="produtos[${idx}][quantidade]" value="${qtd}"></td>
                    <td style="font-weight: bold; color: #2E8B57;">${preco}<input type="hidden" name="produtos[${idx}][preco_unitario]" value="${preco}"></td>
                    <td>${dsct}<input type="hidden" name="produtos[${idx}][desconto]" value="${dsct}"></td>
                    <td style="font-weight: bold; color: #2E8B57;">${total}</td>
                    <td>${resumoTabelas}${montarInputsTabelasEnt(idx, tabelasEntTmp)}</td>
                    <td>
                        <button type="button" class="editar btn btn-success btn-sm mt-1 mb-1"><i class="fa-solid fa-pen-to-square"></i></button>
                        <button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `);
            const $novaLinha = $(`#tabela-produtos tbody tr[data-id="${idx}"]`);
            $novaLinha.find('.task-checkbox').prop('checked', false);
            $("#select-all").prop('checked', false);
        }
        calcTotalEntrada();
        marcaTmp = $("#id_marcaProd").val();
        grupoTmp = $("#id_grupoProd").val();
        unidadeTmp = $("#id_unidProduto").val();
        $("#id_desc_prod, #id_unidProduto, #id_grupoProd, #id_marcaProd, #id_cod_produto").val("");
        $("#id_quantidade").val("1.00");
        $("#id_preco_unit").val("0.00");
        $("#id_desconto").val("0.00");
        $("#id_tabelaEnt").val("");
        $("#id_margem").val("0.00");
        $("#id_vl_tabEnt").val("0.00");
        tabelasEntTmp = [];
        trEditTabEnt = null;
        renderTabelasEntModal();
        $('#edProdModal').modal('hide');
        toast(`${ic_verde} Registro salvo com sucesso!`, cor_verde);
    });
    $("#cancelar-produto-lista").click(function () {
        trEditando = null;
        $("#id_desc_prod, #id_unidProduto, #id_grupoProd, #id_cod_produto, #id_marcaProd").val("");
        $("#id_quantidade").val("1.00");
        $("#id_preco_unit").val("0.00");
        $("#id_desconto").val("0.00");
        $("#id_tabelaEnt").val("");
        $("#id_margem").val("");
        $("#id_vl_tabEnt").val("");
        tabelasEntTmp = [];
        trEditTabEnt = null;
        renderTabelasEntModal();
        $("#id_cod_produto").prop("disabled", false);
        $("#add-prod").prop("readonly", false);
    });
    // excluir linha
    $(document).on("click", ".remover", function () {
        $(this).closest("tr").remove();
        calcTotalEntrada();
        calcTotalPedido();
    });
    // editar linha
    $(document).on("click", ".editar", async function () {
        trEditando = $(this).closest("tr");
        let idx = trEditando.data("id");
        let cod = trEditando.find(`input[name="produtos[${idx}][codigo]"]`).val();
        let prod = trEditando.find(`input[name="produtos[${idx}][produto]"]`).val();
        let qtd = trEditando.find(`input[name="produtos[${idx}][quantidade]"]`).val().replace(',', '.');
        let preco = trEditando.find(`input[name="produtos[${idx}][preco_unitario]"]`).val().replace(',', '.');
        let dsct = trEditando.find(`input[name="produtos[${idx}][desconto]"]`).val().replace(',', '.');
        tabelasEntTmp = carregarTabelasEntDaLinha(idx, trEditando) || [];
        trEditTabEnt = null;
        $("#id_cod_produto").val(cod).prop("disabled", true);
        $("#add-prod").prop("readonly", true);
        $("#id_desc_prod").val(prod);
        $("#id_quantidade").val(qtd);
        $("#id_preco_unit").val(preco);
        $("#id_desconto").val(dsct);
        try {
            const dados = await buscarDadosProduto(cod);
            $("#id_unidProduto").val(dados.unidProd || "");
            $("#id_marcaProd").val(dados.marca || "");
            $("#id_grupoProd").val(dados.grupo || "");
            if (!tabelasEntTmp.length) {
                const respTabs = await carregarTabelasProdutoAjax(dados.id);
                tabelasEntTmp = respTabs.tabelas || [];
            }
        } catch (e) {
            $("#id_unidProduto").val("");
            $("#id_marcaProd").val("");
            $("#id_grupoProd").val("");
            tabelasEntTmp = [];
            toast(`${ic_vermelho} ${e.message}`, cor_vermelho);
        }
        renderTabelasEntModal();
        resetBtnTabEnt();
        setTimeout(() => $('#edProdModal').modal('show'), 200);
    });
    // Pedidos
    $("#add-produto-listaP").click(async function () {
        let cod   = $('#id_cod_produtoP').val();
        let prod  = $("#id_desc_prodP").val();
        let qtd   = $("#id_quantidadeP").val();
        let preco = $("#id_preco_unitP").val();
        let dsct  = $("#id_desc_acres").val();
        let qtdNum   = parseFloat(String(qtd).replace(",", ".")) || 0;
        let precoNum = parseFloat(String(preco).replace(",", ".")) || 0;
        let dsctNum  = parseFloat(String(dsct).replace(",", ".")) || 0;
        let altValor = $('#id_alt_vlP').val();
        let atb  = ($('#id_atribuir').val() || '').trim().toLowerCase();        // desconto/acréscimo
        let tipo = ($('#id_tipo_desc_acres').val() || '').trim().toLowerCase(); // valor/percentual
        // 🔥 CÁLCULO CORRETO
        let totalBase = precoNum * qtdNum;
        let total = totalBase;
        let valorDescReais = 0;
        if (atb === "desconto") {
            if (tipo === "valor") {
                total -= dsctNum;
                valorDescReais = dsctNum;
            } else if (tipo === "percentual") {
                total -= totalBase * (dsctNum / 100);
                valorDescReais = totalBase * (dsctNum / 100);
            }
        }
        else if (atb === "acréscimo" || atb === "acrescimo") {
            if (tipo === "valor") {
                total += dsctNum;
                valorDescReais = dsctNum;
            } else if (tipo === "percentual") {
                total += totalBase * (dsctNum / 100);
                valorDescReais = totalBase * (dsctNum / 100);
            }
        }
        if (total < 0) total = 0;
        total = total.toFixed(2);
        // 🔥 TEXTO FORMATADO
        let sinal = atb === "desconto" ? "-" : "+";
        let cor   = atb === "desconto" ? "#dc3545" : "#198754";
        let textoDesc = "";
        // 🔥 Só mostra se for maior que ZERO
        if (dsctNum > 0) {
            if (tipo === "valor") {
                textoDesc = `<span style="color:${cor}; font-weight:bold;">${sinal} R$ ${dsct}</span>`;
            }
            else if (tipo === "percentual") {
                textoDesc = `<span style="color:${cor}; font-weight:bold;">${sinal} ${dsct}%</span>`;
            }
        } else {
            textoDesc = `<span class="text-muted fw-bold">0.00</span>`;
        }

        // 🔴 VALIDAÇÕES
        if (!cod) {
            toast(`${ic_amarelo} Informe o código do produto!`, cor_amarelo);
            return;
        }
        if (precoNum <= 0) {
            toast(`${ic_amarelo} Preço Unitário deve ser informado!`, cor_amarelo);
            return;
        }
        if (qtdNum <= 0) {
            toast(`${ic_amarelo} Quantidade deve ser informada!`, cor_amarelo);
            return;
        }

        // ✏️ EDITAR
        if (trEditando) {

            let idx = trEditando.data("id");

            trEditando.find("td:eq(0)").html(`${cod}<input type="hidden" name="produtos[${idx}][codigo]" value="${cod}">`);

            trEditando.find("td:eq(1)").html(`${prod}<input type="hidden" name="produtos[${idx}][produto]" value="${prod}">`);

            trEditando.find("td:eq(2)").html(`${qtd}<input type="hidden" name="produtos[${idx}][quantidade]" value="${qtd}">`);

            trEditando.find("td:eq(3)").html(`
                ${preco}
                <input type="hidden" name="produtos[${idx}][preco_unitario]" value="${preco}">
                <input type="hidden" name="produtos[${idx}][alt_valor]" value="${altValor}">
            `);

            trEditando.find("td:eq(4)").html(`
                ${textoDesc}
                <input type="hidden" name="produtos[${idx}][desconto]" value="${dsct}">
                <input type="hidden" name="produtos[${idx}][tipo_desc]" value="${tipo}">
                <input type="hidden" name="produtos[${idx}][operacao]" value="${atb}">
                <input type="hidden" name="produtos[${idx}][valor_desc_real]" value="${valorDescReais}">
            `);

            trEditando.find("td:eq(5)").html(`<span style="font-weight:bold; color:#2E8B57;">${total}</span>`);

            trEditando = null;

            $('#edProdModalP').modal('hide');

        }
        // ➕ ADICIONAR
        else {

            let idx = contador++;

            $("#tabela-produtos tbody tr.vazio").remove();

            let codigoJaExiste = false;

            $("#tabela-produtos tbody input[name*='[codigo]']").each(function () {
                if ($(this).val() === cod) {
                    codigoJaExiste = true;
                    return false;
                }
            });

            if (codigoJaExiste) {
                toast(`${ic_amarelo} O código "${cod}" já está incluso na listagem!`, cor_amarelo);
                return;
            }

            $("#tabela-produtos tbody").append(`
                <tr data-id="${idx}">
                    <td>${cod}<input type="hidden" name="produtos[${idx}][codigo]" value="${cod}"></td>

                    <td>${prod}<input type="hidden" name="produtos[${idx}][produto]" value="${prod}"></td>

                    <td>${qtd}<input type="hidden" name="produtos[${idx}][quantidade]" value="${qtd}"></td>

                    <td style="font-weight:bold; color:#2E8B57;">
                        ${preco}
                        <input type="hidden" name="produtos[${idx}][preco_unitario]" value="${preco}">
                        <input type="hidden" name="produtos[${idx}][alt_valor]" value="${altValor}">
                    </td>

                    <td>
                        ${textoDesc}
                        <input type="hidden" name="produtos[${idx}][desconto]" value="${dsct}">
                        <input type="hidden" name="produtos[${idx}][tipo_desc]" value="${tipo}">
                        <input type="hidden" name="produtos[${idx}][operacao]" value="${atb}">
                        <input type="hidden" name="produtos[${idx}][valor_desc_real]" value="${valorDescReais}">
                    </td>

                    <td style="font-weight:bold; color:#2E8B57;">${total}</td>

                    <td>
                        <button type="button" class="editarP btn btn-success btn-sm mt-1 mb-1">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                        <button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `);

            toast(`${ic_verde} Produto inserido com sucesso!`, cor_verde);
        }

        // 🔄 RESET
        calcTotalPedido();

        $("#id_desc_prodP, #id_unidProdutoP, #id_grupoProdP, #id_marcaProdP, #id_cod_produtoP").val("");

        $("#id_quantidadeP").val("1.00");
        $("#id_preco_unitP, #id_vl_total_preco").val("0.00");
        $("#id_desc_acres").val("0.00");
        $("#id_alt_vlP").val("Não");
        $("#id_cod_produtoP").focus();
    });
    // Cancelar edição/adição de produto na lista de Pedidos
    $("#cancelar-produto-listaP").click(function () {
        trEditando = null;
        $("#id_desc_prodP, #id_unidProdutoP, #id_grupoProdP, #id_marcaProdP, #id_cod_produtoP").val("");
        $("#id_quantidadeP").val("1.00");
        $("#id_preco_unitP").val("0.00");
        $("#id_desc_acres").val("0.00");
        $("#id_alt_vlP").val("Não");
        $('#id_cod_produtoP').prop('disabled', false);
        $('#add-prodP').prop('readonly', false);
    });
    // editar linha de Pedidos
    $(document).on("click", ".editarP", async function () {
        trEditando = $(this).closest("tr");
        let idx = trEditando.data("id");
        let cod   = trEditando.find(`input[name="produtos[${idx}][codigo]"]`).val();
        let prod  = trEditando.find(`input[name="produtos[${idx}][produto]"]`).val();
        let alt_vl = trEditando.find(`input[name="produtos[${idx}][alt_valor]"]`).val();
        let qtd   = trEditando.find(`input[name="produtos[${idx}][quantidade]"]`).val().replace(',', '.');
        let preco = trEditando.find(`input[name="produtos[${idx}][preco_unitario]"]`).val().replace(',', '.');
        let dsct = parseFloat((trEditando.find(`input[name="produtos[${idx}][valor_desc_real]"]`).val() || "0").toString().replace(/\./g, '').replace(',', '.'));
        // 🔥 NOVOS CAMPOS
        let tipo = trEditando.find(`input[name="produtos[${idx}][tipo_desc]"]`).val();
        let operacao = trEditando.find(`input[name="produtos[${idx}][operacao]"]`).val();
        // 🔧 PREENCHER CAMPOS
        $("#id_cod_produtoP").val(cod).prop("disabled", true);
        $("#add-prodP").prop("readonly", true);
        $("#id_desc_prodP").val(prod);
        $("#id_quantidadeP").val(qtd);
        $("#id_preco_unitP").val(preco);
        $("#id_alt_vlP").val(alt_vl);
        $("#id_desc_acres").val((dsct || 0).toFixed(2));
        // 🔥 RESTAURAR SELECTS
        $("#id_tipo_desc_acres").val(
            tipo === "percentual" ? "Percentual" : "Valor"
        );
        $("#id_atribuir").val(
            operacao === "desconto" ? "Desconto" : "Acréscimo"
        );
        // 🔄 ATUALIZA VISUAL
        atualizarLabel();
        calcularTotal();
        try {
            const dados = await buscarDadosProduto(cod);
            $("#id_unidProdutoP").val(dados.unidProd || "");
            $("#id_marcaProdP").val(dados.marca || "");
            $("#id_grupoProdP").val(dados.grupo || "");
        } catch (e) {
            $("#id_unidProdutoP").val("");
            $("#id_marcaProdP").val("");
            $("#id_grupoProdP").val("");
            toast(`${ic_vermelho} ${e.message}`, cor_vermelho);
        }
        setTimeout(() => $('#edProdModalP').modal('show'), 200);
    });
    // Função para calcular desconto/acréscimo em Pedido
    function calcularPreviewDesconto() {
        let totalBase = 0;
        $('#tabela-produtos tbody tr').each(function () {
            let preco = $(this).find('input[name*="[preco_unitario]"]').val();
            let qtd   = $(this).find('input[name*="[quantidade]"]').val();
            let precoNum = parseFloat(String(preco).replace(',', '.')) || 0;
            let qtdNum   = parseFloat(String(qtd).replace(',', '.')) || 0;
            totalBase += precoNum * qtdNum;
        });
        $('#valor-base').text('R$ ' + totalBase.toFixed(2));
        let tipo = $('#tipo_desconto').val();
        let operacao = $('#operacao').val();
        let valor = parseFloat($('#campo_desconto').val().replace(',', '.')) || 0;
        let ajuste = 0;
        if (tipo === 'valor') {
            ajuste = valor;
        } else {
            ajuste = totalBase * (valor / 100);
        }
        let totalFinal = totalBase;
        if (operacao === 'desconto') {
            totalFinal -= ajuste;
        } else {
            totalFinal += ajuste;
        }
        if (totalFinal < 0) totalFinal = 0;
        $('#valor-final').text('R$ ' + totalFinal.toFixed(2));
    }
    $('#modalDesconto').on('shown.bs.modal', function () {
        $('#campo_desconto').val('0.00');
        calcularPreviewDesconto();
    });
    $('#campo_desconto, #tipo_desconto, #operacao').on('input change keyup', function () {
        calcularPreviewDesconto();
    });
    $('#btn-ajuste').click(function() {
        let tipo = $('#operacao').val(); // desconto ou acrescimo
        if (tipo === 'desconto') {
            $(this).data('permissao', 'pedidos.atribuir_desconto_ped');
            $(this).data('acao', 'atribuir_desconto');
        } else {
            $(this).data('permissao', 'pedidos.atribuir_acrescimo_ped');
            $(this).data('acao', 'atribuir_acrescimo');
        }
    });
    $('#add-produtosP').click(function () {
        setTimeout(() => {
            $('#id_cod_produtoP').focus();
        }, 100); // 100ms é suficiente
    });
    $('#confirmarDesconto').click(function () {
        let tipo = $('#tipo_desconto').val(); // valor | percentual
        let operacao = $('#operacao').val(); // desconto | acrescimo
        let valor = parseFloat($('#campo_desconto').val().replace(',', '.')) || 0;
        if (valor < 0) {
            toast(`${ic_amarelo} Informe um valor válido!`, cor_amarelo);
            return;
        }
        let totalBase = 0;
        let itens = [];
        $('#tabela-produtos tbody tr').each(function () {
            let tr = $(this);
            let preco = tr.find('input[name*="[preco_unitario]"]').val();
            let qtd   = tr.find('input[name*="[quantidade]"]').val();
            let precoNum = parseFloat(String(preco).replace(',', '.')) || 0;
            let qtdNum   = parseFloat(String(qtd).replace(',', '.')) || 0;
            let totalItem = precoNum * qtdNum;
            itens.push({
                tr: tr,
                total: totalItem
            });
            totalBase += totalItem;
        });
        if (totalBase <= 0) return;
        let valorTotalAjuste = 0;
        if (tipo === 'valor') {
            valorTotalAjuste = valor;
        } else {
            valorTotalAjuste = totalBase * (valor / 100);
        }
        let acumulado = 0;
        itens.forEach((item, index) => {
            let proporcao = item.total / totalBase;
            let valorRateado;
            if (index === itens.length - 1) {
                valorRateado = valorTotalAjuste - acumulado;
            } else {
                valorRateado = parseFloat((valorTotalAjuste * proporcao).toFixed(2));
                acumulado += valorRateado;
            }
            let totalFinal = item.total;
            if (operacao === "desconto") {
                totalFinal -= valorRateado;
            } else {
                totalFinal += valorRateado;
            }
            if (totalFinal < 0) totalFinal = 0;
            let idx = item.tr.data("id");
            let sinal = operacao === "desconto" ? "-" : "+";
            let cor;
            let texto = "";

            if (Math.abs(valorRateado) < 0.001) {
                texto = `0.00`;
                cor = "#000"; // 🔴 preto
            } else {
                cor = operacao === "desconto" ? "#dc3545" : "#198754";

                texto = tipo === "valor"
                    ? `${sinal} R$ ${valorRateado.toFixed(2)}`
                    : `${sinal} ${((valorRateado / item.total) * 100).toFixed(2)}%`;
            }
            item.tr.find("td:eq(4)").html(`
                <span style="color:${cor}; font-weight:bold;">${texto}</span>
                <input type="hidden" name="produtos[${idx}][desconto]" value="${valorRateado.toFixed(2)}">
                <input type="hidden" name="produtos[${idx}][tipo_desc]" value="valor">
                <input type="hidden" name="produtos[${idx}][operacao]" value="${operacao}">
                <input type="hidden" name="produtos[${idx}][valor_desc_real]" value="${valorRateado.toFixed(2)}">
            `);
            item.tr.find("td:eq(5)").html(`
                <span style="font-weight:bold; color:#2E8B57;">
                    ${totalFinal.toFixed(2)}
                </span>
            `);
        });
        // 🔄 RECALCULA TOTAL
        calcTotalPedido();
        $('#modalDesconto').modal('hide');
        toast(`${ic_verde} ${operacao === "desconto" ? "Desconto" : "Acréscimo"} aplicado com sucesso!`, cor_verde);
    });
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== "") {
            let cookies = document.cookie.split(";");
            for (let i = 0; i < cookies.length; i++) {
                let cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + "=")) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function salvarTabelasProdutoAjax(produtoId, tabelas) {
        return $.ajax({url: "/produtos/ajax/salvar-tabelas/", type: "POST", contentType: "application/json", headers: {"X-CSRFToken": getCookie("csrftoken")}, data: JSON.stringify({produto_id: produtoId, tabelas: tabelas})});
    }
    function carregarTabelasProdutoAjax(produtoId) {
        return $.ajax({url: "/produtos/ajax/buscar-tabelas/", type: "GET", data: { produto_id: produtoId }});
    }
    // Entrada de Produtos
    function buscarProduto(config) {
        const {inputCod, desc, marca, unid, grupo, preco, extrasReset = [], focoFinal, aposCarregar} = config;
        $(inputCod).on('blur keydown', function (event) {
            if (event.type === 'blur' || event.key === 'Enter') {
                if (event.key === 'Enter') event.preventDefault();
                const productId = $(this).val();
                if (productId.trim() === '') {
                    $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                    return;
                }
                $.ajax({
                    url: '/produtos/lista_ajax_ent/',
                    method: 'GET',
                    data: { s: productId, tp: 'cod' },
                    success: async function (response) {
                        if (response.produtos.length > 0) {
                            const p = response.produtos[0];
                            $(desc).val(p.desc_prod || '');
                            $(marca).val(p.marca || '');
                            $(unid).val(p.unidProd || '');
                            $(grupo).val(p.grupo || '');
                            $(preco).val((p.vl_compra || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}));
                            // Reset campos extras
                            extrasReset.forEach(campo => {
                                $(campo.selector).val(campo.valor);
                            });
                            if (typeof aposCarregar === 'function') {
                                aposCarregar();
                            }
                            try {
                                const respTabs = await carregarTabelasProdutoAjax(p.id);
                                tabelasEntTmp = respTabs.tabelas || [];
                                trEditTabEnt = null;
                                renderTabelasEntModal();
                            } catch (e) {
                                tabelasEntTmp = [];
                                renderTabelasEntModal();
                            }
                            if (focoFinal) $(focoFinal).focus();
                        } else {
                            toast(`${ic_amarelo} Código de produto não encontrado!`, cor_amarelo);
                            $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                        }
                    },
                    error: function () {
                        toast(`${ic_vermelho} Erro ao buscar o produto. Tente novamente!`, cor_vermelho);
                        $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                    }
                });
            }
        });
    }
    // Entrada:
    buscarProduto({
    inputCod: '#id_cod_produto', desc: '#id_desc_prod', marca: '#id_marcaProd', unid: '#id_unidProduto', grupo: '#id_grupoProd', preco: '#id_preco_unit', focoFinal: '#id_quantidade',
        extrasReset: [
            { selector: '#id_quantidade', valor: '0.00' },{ selector: '#id_desconto', valor: '0.00' },{ selector: '#id_margem', valor: '0.00' },{ selector: '#id_vl_tabEnt', valor: '0.00' }
        ]
    });
    // Pedido:
    buscarProduto({
    inputCod: '#id_cod_produtoP',desc: '#id_desc_prodP',marca: '#id_marcaProdP',unid: '#id_unidProdutoP',grupo: '#id_grupoProdP',preco: '#id_preco_unitP',focoFinal: '#id_quantidadeP',
        extrasReset: [
            { selector: '#id_desc_acresP', valor: '0.00' },{ selector: '#id_quantidadeP', valor: '1.00' },
        ],
        aposCarregar: function () {
            calcularTotal(); // ✅ agora funciona certo
        }
    });
    $(document).on('click', '.prod-selec', function() {
        const id = $(this).data('id');
        const desc = $(this).data('desc');
        const marc = $(this).data('marc');
        const gp = $(this).data('gp');
        const unid = $(this).data('unid');
        const vl = $(this).data('vl');
        const vl_compra = $(this).data('vl-compra');
        $('#id_desc_prod, #id_marcaProd, #id_unidProduto, #id_grupoProd, #id_preco_unit').val('');
        $('#id_desc_prodP, #id_marcaProdP, #id_unidProdutoP, #id_grupoProdP, #id_preco_unitP').val('');
        $('#id_cod_produto, #id_cod_produtoP').val(id);
        $('#id_desc_prod, #id_desc_prodP').val(desc);
        $('#id_marcaProd, #id_marcaProdP').val(marc);
        $('#id_grupoProd, #id_grupoProdP').val(gp);
        $('#id_unidProduto, #id_unidProdutoP').val(unid);
        $('#id_preco_unit, #id_preco_unitP').val(vl_compra.toFixed(2));
        $('#produtoModal').modal('hide'); // Fecha o modal após a seleção
        $('#id_quantidade, #id_quantidadeP').focus();
    });
    function carregarProdutos(page = 1) {
        const termo = $('#campo-pesquisa-produto').val();
        const tipo = $('#campo-tipo-produto').val();
        const marca = $('#campo-marca-produto').val();
        const grupo = $('#campo-grupo-produto').val();
        const unidade = $('#campo-unidade-produto').val();
        const pagina = $('#campo-pagina').val();
        $.ajax({
            url: '/produtos/lista_ajax_ent/', method: 'GET', data: {s: termo, tp: 'desc', tp_prod: tipo, gp_prod: grupo, marc_prod: marca, unid_prod: unidade, num_pag: pagina, page: page},
            success: function(response) {
                const tabela = $('#produtos-lista');
                tabela.empty();
                if (response.produtos.length > 0) {
                    response.produtos.forEach(produto => {
                        let corEstoque = ""
                        if (produto.estoque_prod > 0) {corEstoque = "fw-bold text-success";}
                        else if (produto.estoque_prod < 0) {corEstoque = "fw-bold text-danger";}
                        else if (produto.estoque_prod === 0) {corEstoque = "fw-bold text-secondary";}
                        const row = `
                            <tr>
                                <td style="width: 10px;">
                                    <button class="btn btn-sm btn-dark prod-selec" data-id="${produto.id}" data-desc="${produto.desc_prod}" data-vl-compra="${produto.vl_compra}" data-marc="${produto.marca}" data-gp="${produto.grupo}" data-unid="${produto.unidProd}" data-vl="${produto.vl_prod}" title="Selecionar" style="margin-left: 9px;">
                                        <i class="fa-regular fa-hand-pointer"></i>
                                    </button>
                                </td>
                                <td style="width: 10px;">${produto.id}</td>
                                <td>${produto.desc_prod}</td>
                                <td style="width: 20px;">${produto.tp_prod}</td>
                                <td style="width: 20px;">${produto.marca}</td>
                                <td style="width: 20px;">${produto.grupo}</td>
                                <td style="width: 20px;">${produto.unidProd}</td>
                                <td style="width: 20px;"><span class="${corEstoque}">${produto.estoque_prod}</span></td>
                                <td style="width: 20px;">${Number(produto.vl_prod || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                }
                else {tabela.append('<tr><td colspan="9" class="text-center">Nenhum produto encontrado.</td></tr>');}
                const paginacao = $('#paginacao');
                paginacao.empty();
                if (response.num_pages > 1) {
                    if (response.has_prev) {paginacao.append(`<button class="btn btn-sm btn-outline-dark pag-btn" data-page="${response.page - 1}">Anterior</button>`);}
                    for (let i = 1; i <= response.num_pages; i++) {
                        paginacao.append(`<button class="btn btn-sm ${i === response.page ? 'btn-dark' : 'btn-outline-dark'} pag-btn" data-page="${i}">${i}</button>`);
                    }
                    if (response.has_next) {paginacao.append(`<button class="btn btn-sm btn-outline-dark pag-btn" data-page="${response.page + 1}">Próximo</button>`);}
                }
            }
        });
    }
    $('#campo-pesquisa-produto').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            const termo = $(this).val().trim();
            if (termo !== '') {$('#pesq-produtos').click();}
        }
    });
    $('#pesq-produtos').on('click', function() {carregarProdutos(1);});
    $(document).on('click', '.pag-btn', function() {
        const page = $(this).data('page');
        carregarProdutos(page);
    });
    // Teste de entrada por XML
    let xmlImportado = null;
    let xmlArquivoSelecionado = null;
    function formatEn(valor) {
        const num = Number(valor || 0);
        return num.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
    }
    function isoParaBr(dataIso) {
        if (!dataIso) return '';
        const [ano, mes, dia] = dataIso.split('-');
        return `${dia}/${mes}/${ano}`;
    }
    $('#btn-importar-xml').on('click', function () {
        $('#input-xml').trigger('click');
    });
    $('#input-xml').on('change', function () {
        const file = this.files[0];
        if (!file) return;
        xmlArquivoSelecionado = file;
        const formData = new FormData();
        formData.append('xml', file);
        formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
        $.ajax({
            url: '/entradas/ler_xml/', method: 'POST', data: formData, processData: false, contentType: false,
            success: function (resp) {
                if (!resp.ok) {
                    toast(`${ic_vermelho} ${resp.erro ? resp.erro : 'Erro ao ler XML.'}`, cor_vermelho);
                    return;
                }
                montarModalXml(resp);
                new bootstrap.Modal(document.getElementById('xmlPreviewModal')).show();
                $('#input-xml').val('');
                fecharLoading();
            },
            error: function (xhr) {
                toast(`${ic_vermelho} ${xhr.responseJSON?.erro ? xhr.responseJSON?.erro : 'Erro ao ler XML.'}`, cor_vermelho);
                $('#input-xml').val('');
                fecharLoading();
            }
        });
    });
    function mascararCpfCnpj(valor) {
        const v = String(valor || '').replace(/\D/g, '');
        if (v.length === 11) {return v.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');}
        if (v.length === 14) {return v.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5');}
        return valor || '';
    }
    function montarModalXml(resp) {
        xmlImportado = resp;
        const nomeFornecedor = resp.fornecedor.razao_social || resp.fornecedor.fantasia || '';
        const docFornecedor = (resp.fornecedor.cpf_cnpj || resp.fornecedor.cnpj || resp.fornecedor.cpf || '');
        const docFornecedorFormatado = mascararCpfCnpj(docFornecedor);
        $('#xml-dados-nota').html(`
            <div class="row g-2">
                <div class="col-md-1">
                    <label class="form-label mb-1">Modelo</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${resp.nota.modelo || ''}">
                </div>
                <div class="col-md-1">
                    <label class="form-label mb-1">Série</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${resp.nota.serie || ''}">
                </div>
                <div class="col-md-1">
                    <label class="form-label mb-1">Número</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${resp.nota.numero || ''}">
                </div>
                <div class="col-md-2">
                    <label class="form-label mb-1">Emissão</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${resp.nota.data_emissao || ''}">
                </div>
                <div class="col-md-3">
                    <label class="form-label mb-1">Chave de Acesso</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" style="font-size: 11px;" readonly value="${resp.nota.chave || ''}">
                </div>
                <div class="col-md-3">
                    <label class="form-label mb-1">Natureza de Operação</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${resp.nota.nat_op || ''}">
                </div>
                <div class="col-md-1">
                    <label class="form-label mb-1">Total</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold text-end" readonly value="${formatEn(resp.nota.total)}">
                </div>
            </div>
        `);
        $('#xml-dados-fornecedor').html(`
            <div class="row g-2 align-items-end">
                <div class="col-md-5">
                    <label class="form-label mb-1">Fornecedor</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${nomeFornecedor}">
                </div>
                <div class="col-md-3">
                    <label class="form-label mb-1">CPF/CNPJ</label>
                    <input type="text" id="xml-doc-fornecedor" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${docFornecedorFormatado}">
                </div>
                <div class="col-md-2">
                    <label class="form-label mb-1">IE</label>
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold" readonly value="${resp.fornecedor.ie || ''}">
                </div>
                <div class="col-md-2 text-end">
                    ${
                        resp.fornecedor.existe ? `<label class="form-label mb-1 d-block">&nbsp;</label><span class="badge bg-success w-100 py-2">Já cadastrado</span>` : `<label class="form-label mb-1 d-block">&nbsp;</label>
                            <button type="button" class="btn btn-warning btn-sm w-100" id="btn-criar-fornecedor-xml">Criar fornecedor</button>`
                    }
                </div>
            </div>
        `);
        const linhas = resp.itens.map((item, i) => {
            const produtoVinculadoId = item.produto_vinculado?.id || '';
            const produtoVinculadoDesc = item.produto_vinculado?.descricao || '';
            const statusVinculo = produtoVinculadoId
                ? `<div class="small text-success fw-semibold produto-vinculado-box">
                        <i class="fa-solid fa-link me-1" title="Produto Vinculado"></i> <span class="produto-vinculado-texto">${produtoVinculadoId} - ${produtoVinculadoDesc}</span>
                    </div>`
                : `<div class="small text-secondary produto-vinculado-box">
                        <i class="fa-solid fa-circle-info me-1"></i> <span class="produto-vinculado-texto">Sem vínculo</span>
                    </div>`;
            return `
                <tr data-idx="${i}">
                    <td style="text-align: center; padding-top: 8px; cursor: pointer;" onclick="toggleTaskCheckboxXML(this)">
                        <input type="checkbox" class="form-check-input task-checkbox-xml" name="multi" value="${item.codigo_fornecedor}" onclick="event.stopPropagation(); checkIfAllSelectedXML(); updateMassChangesButtonXML();">
                    </td>
                    <td class="text-center">${i + 1}</td>
                    <td>${item.codigo_fornecedor || ''}</td>
                    <td>${item.descricao || ''}</td>
                    <td class="text-center">${item.unidade || ''}</td>
                    <td class="text-end">${formatEn(item.quantidade)}</td>
                    <td class="text-end">${formatEn(item.valor_unitario)}</td>
                    <td class="text-end">${formatEn(item.desconto)}</td>
                    <td class="text-end">${formatEn(item.subtotal)}</td>
                    <td class="produto-vinculado-cell" style="min-width:260px;">${statusVinculo}</td>
                    <td class="text-center" style="width:90px;">
                        <div class="btn-group dropstart">
                            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">Ações</button>
                            <ul class="dropdown-menu">
                                <li><a class="dropdown-item acao-vincular-produto" href="#" data-idx="${i}"><i class="fa-solid fa-link me-2"></i>Vincular</a></li>
                                <li><a class="dropdown-item acao-criar-produto" href="#" data-idx="${i}"><i class="fa-solid fa-plus me-2"></i>Criar novo</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger acao-limpar-vinculo" href="#" data-idx="${i}"><i class="fa-solid fa-xmark me-2"></i>Limpar vínculo</a></li>
                            </ul>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
        $('#xml-itens-body').html(linhas);
    }
    function abrirModalCriarProdutoXml(idx) {
        const item = xmlImportado.itens[idx];
        $('#xml-produto-idx').val(idx);
        $('#xml-produto-descricao').val(item.descricao || '');
        $('#xml-produto-unidade').val(null).trigger('change');
        $('#xml-produto-grupo').val(null).trigger('change');
        $('#xml-produto-marca').val(null).trigger('change');
        $('#xml-produto-tipo').val('Principal');
        $('#xml-produto-cod-forn').val(item.codigo_fornecedor || '');
        $('#xml-produto-desc-xml').val(item.descricao || '');
        $('#xml-produto-ean').val(item.ean || '');
        $('#xml-produto-ncm').val(item.ncm || '');
        $('#xml-produto-unidade-xml').val(item.unidade || '');
        new bootstrap.Modal(document.getElementById('modalCriarProdutoXml')).show();
    }
    function getItensSelecionados() {
        const selecionados = [];
        $('#xml-itens-body tr').each(function () {
            const $tr = $(this);
            const checkbox = $tr.find('.task-checkbox-xml');
            if (checkbox.is(':checked')) {selecionados.push({idx: Number($tr.data('idx')), item: xmlImportado.itens[Number($tr.data('idx'))]});}
        });
        return selecionados;
    }
    function getProdutosSelecionadosEnt() {
        const selecionados = [];
        $('#tabela-produtos tbody tr').each(function () {
            const $tr = $(this);
            const checkbox = $tr.find('.task-checkbox');
            if (checkbox.is(':checked')) {
                selecionados.push({codigo: $tr.find('input[name*="[codigo]"]').val(), tr: $tr, base_calculo: getVlCompraLinhaEnt($tr)});
            }
        });
        return selecionados;
    }
    function getProdutosSelecionados() {
        return $('#tabelas-lista .task-checkbox:checked').map(function () {
            const $tr = $(this).closest('tr');
            return {codigo: $(this).val(), tr: $tr, base_calculo: 0};
        }).get();
    }
    $(document).on('click', '#mdAttTbPreco', function () {
        const produtos = getProdutosSelecionados();
        if (!produtos.length) {
            toast("Selecione pelo menos um produto!", cor_amarelo);
            return;
        }
        $('#campo_1').val('0,00');
        $('#campo_2').val('0,00');
        $('#tp-atrib').val('0');
        atualizarModoCamposTbPreco();
        calcularPreviewTbPreco(true);
        const el = document.getElementById('attTbPrecModal');
        let modal = bootstrap.Modal.getInstance(el);
        if (!modal) modal = new bootstrap.Modal(el);
        modal.show();
    });
    $(document).on('submit', '#attTbPrecModal form', async function (e) {
        e.preventDefault();
        const produtos = getProdutosSelecionados();
        if (!produtos.length) {
            toast("Selecione pelo menos um produto!", cor_amarelo);
            return;
        }
        const tipo = $('#tp-atrib').val();
        const campo1 = parseDecimalFlex($('#campo_1').val());
        const campo2 = parseDecimalFlex($('#campo_2').val());
        if (!$('#tb-prec').val()) {
            toast("Selecione uma tabela de preço!", cor_amarelo);
            return;
        }
        if (tipo === '0' && campo1 <= 0) {
            toast("Informe uma margem válida!", cor_amarelo);
            return;
        }
        if (tipo === '1' && campo2 <= 0) {
            toast("Informe um valor válido!", cor_amarelo);
            return;
        }
        const payload = {tabela_id: $('#tb-prec').val(), tipo, campo_1: campo1, campo_2: campo2, produtos: produtos.map(p => ({id: p.codigo, base_calculo: p.base_calculo}))};
        iniciarLoading();
        try {
            const resp = await fetch('/produtos/att-tb-preco-lt/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()}, body: JSON.stringify(payload)});
            const data = await resp.json();
            if (!data.ok) {
                toast(data.msg || 'Erro ao atualizar tabela.', cor_vermelho);
                return;
            }
            produtos.forEach(p => {
                atualizarTabelaProdutoEnt(p.tr, data.tabela_nome, data.valores[String(p.codigo)]);
                p.tr.find('.task-checkbox').prop('checked', false);
            });
            $('#select-all').prop('checked', false).prop('indeterminate', false);
            updateMassChangesButton();
            toast("Tabela aplicada com sucesso!", cor_verde);
            bootstrap.Modal.getInstance(document.getElementById('attTbPrecModal'))?.hide();
            finalizarLoading();
        } catch (e) {
            console.error(e);
            toast("Erro na requisição", cor_vermelho);
        } finally {
            fecharLoadingCompleto();
            finalizarLoading();
        }
    });
    let bloqueioCalcTbPreco = false;
    function parseDecimalFlex(valor) {
        if (valor === null || valor === undefined) return 0;
        let s = String(valor).trim();
        if (!s) return 0;
        if (s.includes(',') && s.includes('.')) {
            if (s.lastIndexOf(',') > s.lastIndexOf('.')) {s = s.replace(/\./g, '').replace(',', '.');}
            else {s = s.replace(/,/g, '');}
        }
        else if (s.includes(',')) {s = s.replace(',', '.');}
        const n = parseFloat(s);
        return Number.isFinite(n) ? n : 0;
    }
    function getVlCompraLinhaEnt($tr) {
        const val = $tr.find('input[name*="[preco_unitario]"]').val();
        const num = Number(val);
        return Number.isFinite(num) ? num : 0;
    }
    function atualizarModoCamposTbPreco() {
        const tipo = $('#tp-atrib').val();
        if (tipo === '0') {
            $('#campo_1').prop('readonly', false).removeClass('bg-secondary');
            $('#campo_2').prop('readonly', true).addClass('bg-secondary');
        } else {
            $('#campo_1').prop('readonly', true).addClass('bg-secondary');
            $('#campo_2').prop('readonly', false).removeClass('bg-secondary');
        }
    }
    if ($('#id_num_conta').val() != '') {
        $('#id_num_conta').prop('readonly', true).addClass('bg-secondary');
    } else {
        $('#id_num_conta').prop('readonly', false).removeClass('bg-secondary');
    }
    function calcularPreviewTbPreco(formatarCampos = false) {
        if (bloqueioCalcTbPreco) return;
        const produtos = getProdutosSelecionadosEnt();
        if (!produtos.length) {
            return;
        }
        const $tr = produtos[0].tr;
        const vlCompra = getVlCompraLinhaEnt($tr);
        const tipo = $('#tp-atrib').val();
        let margem = parseDecimalFlex($('#campo_1').val());
        let valor = parseDecimalFlex($('#campo_2').val());
        bloqueioCalcTbPreco = true;
        try {
            if (tipo === '0') {
                valor = vlCompra * (1 + (margem / 100));
                if (formatarCampos) {
                    $('#campo_1').val(formatBR(margem));
                    $('#campo_2').val(formatBR(valor));
                } else {
                    $('#campo_2').val(valor.toFixed(2));
                }
            } else {
                margem = vlCompra > 0 ? ((valor - vlCompra) / vlCompra) * 100 : 0;
                if (formatarCampos) {
                    $('#campo_2').val(formatBR(valor));
                    $('#campo_1').val(formatBR(margem));
                } else {
                    $('#campo_1').val(margem.toFixed(2));
                }
            }
        } finally {
            bloqueioCalcTbPreco = false;
        }
    }
    $(document).on('click', '#mdAttTbPrecoEnt', function () {
        const produtos = getProdutosSelecionadosEnt();
        if (!produtos.length) {
            toast("Selecione pelo menos um produto!", cor_amarelo);
            return;
        }
        $('#campo_1').val('0,00');
        $('#campo_2').val('0,00');
        $('#tp-atrib').val('0');
        atualizarModoCamposTbPreco();
        calcularPreviewTbPreco(true);
        const el = document.getElementById('attTbPrecModalEnt');
        let modal = bootstrap.Modal.getInstance(el);
        if (!modal) modal = new bootstrap.Modal(el);
        modal.show();
    });
    $('#tp-atrib').on('change', function () {
        atualizarModoCamposTbPreco();
        calcularPreviewTbPreco(true);
    });
    $('#campo_1').on('input keyup change', function () {
        if ($('#tp-atrib').val() === '0') {
            calcularPreviewTbPreco(false);
        }
    });
    $('#campo_2').on('input keyup change', function () {
        if ($('#tp-atrib').val() === '1') {
            calcularPreviewTbPreco(false);
        }
    });
    $('#campo_1, #campo_2').on('blur', function () {
        calcularPreviewTbPreco(true);
    });
    $('#attTbPrecModalEnt form').on('submit', async function (e) {
        e.preventDefault();
        const produtos = getProdutosSelecionadosEnt();
        if (!produtos.length) {
            toast("Selecione pelo menos um produto!", cor_amarelo);
            return;
        }
        const tipo = $('#tp-atrib').val();
        const campo1 = parseDecimalFlex($('#campo_1').val());
        const campo2 = parseDecimalFlex($('#campo_2').val());
        if (!$('#tb-prec').val()) {
            toast("Selecione uma tabela de preço!", cor_amarelo);
            return;
        }
        if (tipo === '0' && campo1 <= 0) {
            toast("Informe uma margem válida!", cor_amarelo);
            return;
        }
        if (tipo === '1' && campo2 <= 0) {
            toast("Informe um valor válido!", cor_amarelo);
            return;
        }
        const payload = {tabela_id: $('#tb-prec').val(), tipo: $('#tp-atrib').val(), campo_1: parseDecimalFlex($('#campo_1').val()), campo_2: parseDecimalFlex($('#campo_2').val()),
            produtos: produtos.map(p => ({id: p.codigo, base_calculo: p.base_calculo}))
        };
        iniciarLoading();
        try {
            const resp = await fetch('/produtos/att-tb-preco-lt/', {
                method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()}, body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!data.ok) {
                toast(data.msg || 'Erro ao atualizar tabela.', cor_vermelho);
                return;
            }
            produtos.forEach(p => {
                atualizarTabelaProdutoEnt(p.tr, data.tabela_nome, data.valores[String(p.codigo)]);
                p.tr.find('.task-checkbox').prop('checked', false);
                $('#select-all').prop('checked', false).prop('indeterminate', false);
                updateMassChangesButton();
            });
            toast("Tabela aplicada com sucesso!", cor_verde);
            bootstrap.Modal.getInstance(document.getElementById('attTbPrecModalEnt')).hide();
            finalizarLoading();
        } catch (e) {
            console.error(e);
            toast("Erro na requisição", cor_vermelho);
        } finally {
            fecharLoadingCompleto();
            finalizarLoading();
        }
    });
    function atualizarTabelaProdutoEnt($tr, tabelaNome, dadosTabela) {
        const $cell = $tr.find('td').eq(7);
        const nome = String(tabelaNome || '').toUpperCase();
        const vlProd = Number(dadosTabela?.vl_prod ?? 0);
        const html = `
            <div class="linha-tabela-pill mb-1" data-tabela="${nome}">
                <span>${nome}</span>
                <span>${formatBR(vlProd)}</span>
            </div>
        `;
        $cell.html(html);
    }
    $(document).on('click', '#update-selected', function () {
        const itens = getItensSelecionados();
        const produtos = getProdutosSelecionados();
        if (!itens.length && !produtos.length) {
            toast(`${ic_amarelo} Selecione pelo menos um item!`, cor_amarelo);
            return;
        }
        const temVinculado = itens.some(obj => {return obj.item.produto_vinculado && Number(obj.item.produto_vinculado.id);});
        if (temVinculado) {
            toast(`${ic_amarelo} Existem itens já vinculados. Desmarque-os antes de continuar!`, cor_amarelo);
            return;
        }
        new bootstrap.Modal(document.getElementById('updateModal')).show();
    });
    $(document).on('click', '#update-selected-xml', function () {
        const itens = getItensSelecionados();
        const produtos = getProdutosSelecionados();
        if (!itens.length && !produtos.length) {
            toast(`${ic_amarelo} Selecione pelo menos um item!`, cor_amarelo);
            return;
        }
        const temVinculado = itens.some(obj => {return obj.item.produto_vinculado && Number(obj.item.produto_vinculado.id);});
        if (temVinculado) {
            toast(`${ic_amarelo} Existem itens já vinculados. Desmarque-os antes de continuar!`, cor_amarelo);
            return;
        }
        new bootstrap.Modal(document.getElementById('modalCriarProdutoMassa')).show();
    });
    $('#btn-confirmar-massa').on('click', async function () {
        const itens = getItensSelecionados();
        if (!itens.length) return;
        const payloadBase = {
            fornecedor_id: xmlImportado.fornecedor.id || null, unidade_id: $('#massa-unidade').val() || null, grupo_id: $('#massa-grupo').val() || null,
            marca_id: $('#massa-marca').val() || null, tp_prod: $('#massa-tipo').val() || 'Principal'};
        // 🔥 monta lista de produtos
        const produtos = itens.map(obj => {
            const item = obj.item;
            return {
                idx: obj.idx, ...payloadBase, descricao: item.descricao, codigo_fornecedor: item.codigo_fornecedor || '', descricao_fornecedor: item.descricao || '',
                ean: item.ean || '', ncm: item.ncm || ''};
        });
        iniciarLoading();
        try {
            const resp = await fetch('/entradas/criar_produtos_em_massa/', {
                method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()}, body: JSON.stringify({ produtos })});
            const data = await resp.json();
            if (!data.ok) {
                toast(data.erro || 'Erro ao criar produtos.', cor_vermelho);
                return;
            }
            // 🔄 atualiza tela com retorno
            data.resultados.forEach(r => {
                const produto = r.produto;
                xmlImportado.itens[r.idx].produto_vinculado = {id: produto.id, descricao: produto.descricao};
                const $tr = $(`#xml-itens-body tr[data-idx="${r.idx}"]`);
                atualizarStatusProdutoVinculado($tr, produto.id, produto.descricao);
            });
            toast(`${ic_verde} Produtos processados com sucesso!`, cor_verde);
        } catch (e) {
            console.error(e);
            toast('Erro na requisição', cor_vermelho);
        } finally {
            finalizarLoading();
            bootstrap.Modal.getInstance(document.getElementById('modalCriarProdutoMassa')).hide();
            $('.task-checkbox-xml').prop('checked', false);
            $('#select-all-xml').prop('checked', false);
        }
    });
    $(document).on('click', '#btn-criar-fornecedor-xml', function () {
        if (!xmlArquivoSelecionado) {
            toast(`${ic_amarelo} Arquivo XML não encontrado para criar o fornecedor!`, cor_vermelho);
            return;
        }
        const formData = new FormData();
        formData.append('xml', xmlArquivoSelecionado);
        formData.append('csrfmiddlewaretoken', $('[name=csrfmiddlewaretoken]').val());
        const $btn = $(this);
        $btn.prop('disabled', true).text('Criando...');
        $.ajax({
            url: '/entradas/criar_fornecedor_xml/', method: 'POST', data: formData, processData: false, contentType: false,
            success: function (resp) {
                if (!resp.ok) {
                    toast(resp.erro || 'Erro ao criar fornecedor.', cor_vermelho);
                    return;
                }
                xmlImportado.fornecedor.id = resp.fornecedor.id;
                xmlImportado.fornecedor.existe = true;
                $('#id_fornecedor').val(resp.fornecedor.id).trigger('change');
                const badgeHtml = `
                    <label class="form-label mb-1 d-block">&nbsp;</label>
                    <span class="badge bg-success w-100 py-2">Já cadastrado</span>
                `;
                $('#btn-criar-fornecedor-xml').closest('.col-md-2').html(badgeHtml);
                toast(resp.fornecedor.ja_existia ? 'Fornecedor já existia e foi vinculado.' : 'Fornecedor criado com sucesso.', cor_verde);
            },
            error: function (xhr) {toast(xhr.responseJSON?.erro || 'Erro ao criar fornecedor.', cor_vermelho);},
            complete: function () {$btn.prop('disabled', false).text('Criar fornecedor');}
        });
    });
    $(document).on('click', '.acao-vincular-produto', function (e) {
        e.preventDefault();
        const idx = Number($(this).data('idx'));
        const item = xmlImportado.itens[idx];
        $('#vincular-produto-idx').val(idx);
        $('#vincular-produto-xml-desc').val(item.descricao || '');
        const $select = $('#vincular-produto-select');
        $select.val(null).trigger('change');
        $select.empty().append('<option value=""></option>');
        new bootstrap.Modal(document.getElementById('modalVincularProdutoXml')).show();
    });
    $('#btn-confirmar-criar-produto-xml').on('click', function () {
        const idx = Number($('#xml-produto-idx').val());
        const item = xmlImportado.itens[idx];
        const payload = {
            fornecedor_id: xmlImportado.fornecedor.id || null, descricao: $('#xml-produto-descricao').val().trim(), unidade_id: $('#xml-produto-unidade').val() || null, grupo_id: $('#xml-produto-grupo').val() || null,
            marca_id: $('#xml-produto-marca').val() || null, tp_prod: $('#xml-produto-tipo').val() || 'Principal', codigo_fornecedor: item.codigo_fornecedor || '', descricao_fornecedor: item.descricao || '', ean: item.ean || '', ncm: item.ncm || ''
        };
        if (!payload.descricao) {
            toast(`${ic_amarelo} Informe a descrição do produto!`, cor_amarelo);
            return;
        }
        $.ajax({
            url: '/entradas/criar_produto_xml/', method: 'POST', contentType: 'application/json', headers: {'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()},
            data: JSON.stringify(payload),
            success: function (resp) {
                if (!resp.ok) {
                    toast(resp.erro || 'Erro ao cadastrar produto.', cor_vermelho);
                    return;
                }
                const produto = resp.produto;
                xmlImportado.itens[idx].produto_vinculado = {id: produto.id, descricao: produto.descricao};
                const $tr = $(`#xml-itens-body tr[data-idx="${idx}"]`);
                atualizarStatusProdutoVinculado($tr, produto.id, produto.descricao);
                bootstrap.Modal.getInstance(document.getElementById('modalCriarProdutoXml')).hide();
                toast(`${ic_verde} Produto cadastrado e vinculado!`, cor_verde);
            },
            error: function () {toast('Erro ao cadastrar produto.', cor_vermelho);}
        });
    });
    $('#btn-confirmar-vinculo-produto').on('click', function () {
        const idx = Number($('#vincular-produto-idx').val());
        const produtoId = $('#vincular-produto-select').val();
        const produtoDesc = $('#vincular-produto-select option:selected').text().trim();
        if (!produtoId) {
            toast(`${ic_amarelo} Selecione um produto para vincular`, cor_amarelo);
            return;
        }
        xmlImportado.itens[idx].produto_vinculado = {id: produtoId, descricao: produtoDesc};
        const $tr = $(`#xml-itens-body tr[data-idx="${idx}"]`);
        atualizarStatusProdutoVinculado($tr, produtoId, produtoDesc);
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalVincularProdutoXml'));
        if (modal) modal.hide();
        toast(`${ic_verde} Produto vinculado com sucesso!`, cor_verde);
    });
    $(document).on('click', '.acao-criar-produto', function (e) {
        e.preventDefault();
        const idx = Number($(this).data('idx'));
        abrirModalCriarProdutoXml(idx);
    });
    $(document).on('click', '.acao-limpar-vinculo', function (e) {
        e.preventDefault();
        const idx = Number($(this).data('idx'));
        xmlImportado.itens[idx].produto_vinculado = null;
        const $tr = $(`#xml-itens-body tr[data-idx="${idx}"]`);
        atualizarStatusProdutoVinculado($tr, null, null);
        toast('Vínculo removido.', cor_amarelo);
    });
    function atualizarStatusProdutoVinculado($tr, produtoId, descricao) {
        const $cell = $tr.find('.produto-vinculado-cell');
        if (produtoId && descricao) {
            $cell.html(`
                <div class="small text-success fw-semibold produto-vinculado-box">
                    <i class="fa-solid fa-link me-1"></i> <span class="produto-vinculado-texto">#${produtoId} - ${descricao}</span>
                </div>
            `);
        } else {
            $cell.html(`
                <div class="small text-secondary produto-vinculado-box"><i class="fa-solid fa-circle-info me-1"></i> <span class="produto-vinculado-texto">Sem vínculo</span></div>
            `);
        }
    }
    async function adicionarProdutoEntradaXml(item, index) {
        const $tbody = $('#tabela-produtos tbody');
        const codigo = item.codigo;
        const produto = item.produto || '';
        const qtd = parseFloat(String(item.quantidade || 0).replace(',', '.')) || 0;
        const vlUnit = parseFloat(String(item.preco_unitario || 0).replace(',', '.')) || 0;
        const desconto = parseFloat(String(item.desconto || 0).replace(',', '.')) || 0;
        const total = (qtd * vlUnit) - desconto;
        let resp = await carregarTabelasProdutoAjax(codigo);
        let tabelas = resp.tabelas || [];
        let resumoTabelas = montarResumoTabelasEnt(tabelas);
        let inputsTabelas = montarInputsTabelasEnt(index, tabelas);
        const linha = `
            <tr data-id="${index}">
                <td style="text-align: center; padding-top: 8px; cursor: pointer;" onclick="toggleTaskCheckbox(this)">
                    <input type="checkbox" class="form-check-input task-checkbox" name="multi" value="${codigo}" onclick="event.stopPropagation(); checkIfAllSelected(); updateMassChangesButton();">
                </td>
                <td>${codigo}<input type="hidden" name="produtos[${index}][codigo]" value="${codigo}"></td>
                <td>${produto}<input type="hidden" name="produtos[${index}][produto]" value="${produto}"></td>
                <td>${formatEn(qtd)}<input type="hidden" name="produtos[${index}][quantidade]" value="${qtd.toFixed(2)}"></td>
                <td style="font-weight: bold; color: #2E8B57;">${formatEn(vlUnit)}<input type="hidden" name="produtos[${index}][preco_unitario]" value="${vlUnit.toFixed(2)}"></td>
                <td>${formatEn(desconto)}<input type="hidden" name="produtos[${index}][desconto]" value="${desconto.toFixed(2)}"></td>
                <td style="font-weight: bold; color: #2E8B57;">${total.toFixed(2)}</td>
                <td>${resumoTabelas} ${inputsTabelas}</td>
                <td>
                    <button type="button" class="editar btn btn-success btn-sm mt-1 mb-1"><i class="fa-solid fa-pen-to-square"></i></button>
                    <button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button>
                </td>
            </tr>
        `;
        $tbody.append(linha);
        setTimeout(() => {calcTotalEntrada();}, 50);
    }
    function fecharLoadingCompleto(callback = null) {
        const el = document.getElementById('loadingModal');
        if (!el) {
            if (typeof callback === 'function') callback();
            return;
        }
        const modal = bootstrap.Modal.getInstance(el);
        if (!modal) {
            if (typeof callback === 'function') callback();
            return;
        }
        el.addEventListener('hidden.bs.modal', function handler() {
            el.removeEventListener('hidden.bs.modal', handler);
            document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
            document.body.classList.remove('modal-open');
            document.body.style.paddingRight = '';
            if (typeof callback === 'function') {callback(); }
        });
        fecharLoading();
    }
    $('#confirmar-importacao-xml').on('click', async function () {
        if (!xmlImportado) return;
        if (!xmlImportado.fornecedor || !xmlImportado.fornecedor.id) {
            toast(`${ic_amarelo} Cadastre o fornecedor antes de confirmar a importação!`, cor_amarelo);
            return;
        }
        $('#id_numeracao').val(xmlImportado.nota.numero || '');
        $('#id_tipo').val("Nota Fiscal");
        $('#id_serie').val(xmlImportado.nota.serie || '');
        $('#id_chave_acesso').val(xmlImportado.nota.chave || '');
        $('#id_nat_op').val(xmlImportado.nota.nat_op || '');
        $('#id_modelo').val(xmlImportado.nota.modelo || '');
        $('#id_dt_emi').val(isoParaBr(xmlImportado.nota.data_emissao_input));
        if (xmlImportado.fornecedor.id) {
            const $forn = $('#id_fornecedor');
            const textoFornecedor = xmlImportado.fornecedor.razao_social || xmlImportado.fornecedor.nome || xmlImportado.fornecedor.documento || 'Fornecedor selecionado';
            if ($forn.find(`option[value="${xmlImportado.fornecedor.id}"]`).length === 0) {
                const option = new Option(textoFornecedor, xmlImportado.fornecedor.id, true, true);
                $forn.append(option);
            }
            $forn.val(String(xmlImportado.fornecedor.id)).trigger('change');
        }
        $('#tabela-produtos tbody').html('');
        let itensOrdenados = xmlImportado.itens.filter(item => item.produto_vinculado && Number(item.produto_vinculado.id)).sort((a, b) => Number(a.produto_vinculado.id) - Number(b.produto_vinculado.id));
        if (!itensOrdenados.length) {
            fecharLoadingCompleto();
            toast(`${ic_amarelo} Vincule ou cadastre os produtos antes de confirmar`, cor_amarelo);
            return;
        }
        iniciarLoading();
        for (const [index, item] of itensOrdenados.entries()) {
            await adicionarProdutoEntradaXml({codigo: item.produto_vinculado.id, produto: item.produto_vinculado.descricao || item.descricao, quantidade: parseFloat(item.quantidade || 0), preco_unitario: parseFloat(item.valor_unitario || 0), desconto: parseFloat(item.desconto || 0)}, index);
        }
        calcTotalEntrada();
        const previewEl = document.getElementById('xmlPreviewModal');
        const previewModal = bootstrap.Modal.getInstance(previewEl);
        if (previewModal) {
            $(previewEl).one('hidden.bs.modal', function () {
                fecharLoadingCompleto(function () {
                    toast('Dados do XML carregados no formulário.', cor_verde);
                    finalizarLoading();
                });
            });
            previewModal.hide();
        } else {
            fecharLoadingCompleto(function () {
                toast('Dados do XML carregados no formulário.', cor_verde);
                finalizarLoading();
            });
        }
    });
    function inicializarSelect2VinculoProdutoXml() {
        $('#vincular-produto-select').select2({
            dropdownParent: $('#modalVincularProdutoXml'), width: '100%', placeholder: 'Digite código ou descrição do produto', allowClear: true, language:lingSel,
            minimumInputLength: 1,
            ajax: {
                url: '/produtos/lista_ajax1/', dataType: 'json', delay: 250, data: function (params) {return {s: params.term || '', xml: 1};},
                processResults: function (data) {
                    return {
                        results: (data.produtos || []).map(function (p) {return {id: p.id, text: `${p.id} - ${p.desc_prod}`};})
                    };
                }
            }
        });
    }
    $(document).ready(function () {inicializarSelect2VinculoProdutoXml();});
    // Notificações do Django
    function carregarNotificacoes() {
        $.get('/ajax/notificacoes/', function(response) {
            const notificacoes = Array.isArray(response?.notificacoes) ? response.notificacoes : [];
            const badge = $('.badge-pulse');
            const lista = $('#notificationsDropdown').next('ul.dropdown-menu');
            lista.empty();
            if (notificacoes.length > 0) {
                if (badge.length === 0) {
                    $('#notificationsDropdown').append(`
                        <span class="position-absolute top-0 start-100 translate-middle badge border border-light rounded-circle bg-danger p-2 badge-pulse">
                            <span class="visually-hidden">Notificações não lidas</span>
                        </span>
                    `);
                }
                notificacoes.forEach(n => {
                    lista.append(`
                        <li>
                            <a href="#" class="abrir-modal-solicitacao dropdown-item text-wrap" data-id="${n.solicitacao_id || ''}" data-verb="${n.verb || ''}" data-description="${n.description || ''}">
                                ${n.verb || 'Notificação'}<br>
                                <small class="text-muted text-wrap">Mais informações, clique aqui!</small>
                            </a>
                        </li>
                    `);
                });
            } else {
                badge.remove();
                lista.append(`
                    <li><a href="#" class="dropdown-item disabled text-center">Nenhuma notificação</a></li>
                `);
            }
        }).fail(function(xhr, status, error) {
            console.error('Erro ao carregar notificações:', error);
        });
    }
    setInterval(carregarNotificacoes, 15000);
    carregarNotificacoes();
    function toggleSenhaField() {
        if ($('#id_gerar_senha_lib').is(':checked')) {$('#id_senha_liberacao').prop('disabled', false);}
        else {$('#id_senha_liberacao').prop('disabled', true).val('');}
    }
    toggleSenhaField();
    $('#id_gerar_senha_lib').change(function() {toggleSenhaField();});
    let solicitacaoId = null;
    let timer = null;
    let toastAguardando = null;
    let acaoSelecionada = null;
    // Confirmação do envio da solicitação
    $('#confirmSend').on('click', function() {
        $('#confirmModal').modal('hide');
        $('#userSelectModal').modal('show');
    });
    // Enviar a solicitação
    $('#sendNotification').on('click', function() {
        const usuarioId = $('#userSelect').val();
        $.post('/orcamentos/enviar-solicitacao/', {
            acao: acaoSelecionada, modulo: contextoPermissao.modulo, registro_id: contextoPermissao.registro_id, registro_desc: contextoPermissao.registro_desc, usuario_id: usuarioId, csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
        }, function(data) {
            solicitacaoId = data.id;
            $('#userSelectModal').modal('hide');
            toastAguardando = Toastify({
                text: `<i class="fa-solid fa-stopwatch"></i> Aguardando aprovação para sua solicitação!<div class='spinner-grow text-dark' role='status' style='width: 1rem; height: 1rem;'><span class='visually-hidden'Carregando...</span></div>`,
                duration: 180000, close: false, gravity: "top", position: "center", stopOnFocus: false, escapeMarkup: false, style: {background: "linear-gradient(to right, #6c757d, #adb5bd)", color: "#212529", borderRadius: "8px"}
            });
            toastAguardando.showToast();
            iniciarTimerDeVerificacao(data.expira_em);
        });
    });
    // Verificar status a cada 5 segundos
    function iniciarTimerDeVerificacao(expiraEm) {
        const expira = new Date(expiraEm);
        timer = setInterval(() => {
            const agora = new Date();
            if (agora > expira) {
                clearInterval(timer);
                $.post('/orcamentos/expirar-solicitacao/', {id: solicitacaoId, csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()});
                if (toastAguardando) toastAguardando.hideToast();
                toast(`${ic_padrao} Tempo expirado. A solicitação não foi respondida!`, cor_padrao);
                carregarNotificacoes();
                return;
            }
            $.get(`/orcamentos/verificar-solicitacao/${solicitacaoId}/`, function(data) {
                if (data.status === 'Aprovada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast(`${ic_verde} Solicitação Concedida ao usuário!`, cor_verde);
                    if (acaoSelecionada === "atribuir_desconto") {$('#modalDesconto').modal('show');}
                    else if (acaoSelecionada === "atribuir_acrescimo") {$('#modalAcrescimo').modal('show');}
                } else if (data.status === 'Negada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast(`${ic_vermelho} Solicitação Negada ao usuário!`, cor_vermelho);
                } else if (data.status === 'Expirada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast(`${ic_info} A solicitação expirou!`, cor_padrao);
                }
            });
        }, 5000);
    }
    $('#userSelectModal').on('show.bs.modal', function () {
        $.get('/orcamentos/usuarios-com-permissao/', function (data) {
            const select = $('#userSelect');
            select.empty();
            select.append(`<option value="">------</option>`);
            if (!data.usuarios || data.usuarios.length === 0) {
                select.append(`<option value="">Nenhum usuário disponível</option>`);
                return;
            }
            data.usuarios.forEach(u => {select.append(`<option value="${u.id}">${u.nome}</option>`);});
        });
    });
    $('#liberarAgora').on('click', function () {
        const usuarioId = $('#userSelect').val();
        const senha = $('#senhaLiberacao').val();
        const acao = window.acaoPendente; // você já usa isso no sistema
        if (!usuarioId) {
            toast(`${ic_amarelo} Usuário deve ser informado!`, cor_amarelo);
            return;
        }
        if (!senha) {
            toast(`${ic_amarelo} Digite a senha do Usuário Autorizador!`, cor_amarelo);
            return;
        }
        $.ajax({
            url: '/orcamentos/liberar-com-senha/', type: 'POST', data: {usuario_id: usuarioId, senha: senha, acao: acao, csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()},
            success: function (resp) {
                if (resp.status === 'Aprovada') {
                    $('#userSelectModal').modal('hide');
                    toast(`${ic_verde} Solicitação Concedida ao usuário!`, cor_verde);
                    if (acaoSelecionada === "atribuir_desconto") {$('#modalDesconto').modal('show');}
                    else if (acaoSelecionada === "atribuir_acrescimo") {$('#modalAcrescimo').modal('show');}
                    if (window.acaoCallback) {window.acaoCallback();}
                }
                else {toast(`${ic_vermelho} Senha inserida incorreta!`, cor_vermelho);}
            }
        });
        $('#senhaLiberacao').val('');
    });
    // Ao clicar em uma notificação, abre o modal preenchendo descrição e id
    $(document).on('click', '.abrir-modal-solicitacao', function(e) {
        e.preventDefault();
        const verb = $(this).data('verb');
        const descricao = $(this).data('description') || '';
        $('#modalSolicitacaoLabel').html(`<i class="fa-solid fa-walkie-talkie me-2"></i> ${verb}`);
        const match = verb.match(/ID\s+(\d+)/i);
        const solicitacaoId = match ? match[1] : null;
        console.log('ID capturado:', solicitacaoId);
        if (!solicitacaoId) {
            toast(`${ic_info} ID da solicitação não encontrado!`, cor_info);
            return;
        }
        $('#descricaoSolicitacao').text(descricao);
        $('#solicitacaoId').val(solicitacaoId);
        $('#modalSolicitacao').modal('show');
    });
    // Quando clicar no botão aprovar
    $('#aprovarSolicitacao').on('click', function() {
        const id = $('#solicitacaoId').val();              // pega id da solicitação no modal
        responderSolicitacao(id, 'aprovar');               // chama função para aprovar
        carregarNotificacoes();
    });
    // Quando clicar no botão negar
    $('#negarSolicitacao').on('click', function() {
        const id = $('#solicitacaoId').val();              // pega id da solicitação no modal
        responderSolicitacao(id, 'negar');                 // chama função para negar
        carregarNotificacoes();
    });
    // Função que envia o POST para a view Django que responde a solicitação
    function responderSolicitacao(id, acao) {
        console.log('Enviando resposta:', {id, acao});
        $.post('/orcamentos/responder-solicitacao/', {id: id, acao: acao, csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()}, function(response) {
            $('#modalSolicitacao').modal('hide');
            if (response.status === "Aprovada") {toast(`${ic_verde} Solicitação Concedida ao usuário!`, cor_verde);}
            else {toast(`${ic_vermelho} Solicitação Negada ao usuário!`, cor_vermelho);}
        });
        carregarNotificacoes();
    }
    function verificarOuCriarLocalizacao(estado, cidade, bairro) {return fetch(`/verificar-localizacao/?estado=${estado}&cidade=${cidade}&bairro=${bairro}`).then(response => response.json()).catch(error => console.error('Erro na verificação de localizacao:', error));}
    // Marcar checkboxs de permissões
    $('.check-grupo').on('click', function () {
        const grupo = $(this).data('grupo');
        const todasMarcadas = $(`.check-permissao[data-grupo="${grupo}"]`).length === $(`.check-permissao[data-grupo="${grupo}"]:checked`).length;
        $(`.check-permissao[data-grupo="${grupo}"]`).prop('checked', !todasMarcadas);
    });
    let contextoPermissao = {};
    function verificarPermissaoAntesDeExecutar(perm, onPermitido, onNegado) {
        $.get('/usuarios/ajax/permissao/', { perm: perm }, function(data) {
            if (data.permitido) {onPermitido();}
            else {onNegado();}
        });
    }
    $(document).on('click', '.btn-permissao', function (e) {
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        const $btn = $(this);
        const permissao = $btn.data('permissao');
        const msgNegado = $btn.data('msg-negado') || 'Você não tem permissão para realizar essa ação!';
        const url = $btn.data('url');
        const href = $btn.attr('href');
        const modalTarget = $btn.data('bs-target');
        const acaoSelecionada = $btn.data('acao');
        contextoPermissao = {acao: $btn.data('acao') || '', modulo: $btn.data('modulo') || document.title, registro_id: $btn.data('registro-id') || '', registro_desc: $btn.data('registro-desc') || ''};
        verificarPermissaoAntesDeExecutar(
            permissao,
            function () {
                if ($('#createForm').length) {
                    const isOrcamento = $('.tabela-produtos').length > 0;
                    if (isOrcamento) {
                        const temProdutos = $('.tabela-produtos tbody tr:not(.vazio)').length > 0;
                        const temAdicionais = $('.tabela-adicionais tbody tr:not(.vazio)').length > 0;
                        if (!temProdutos && !temAdicionais) {
                            toast(`${ic_amarelo} Insira ao menos um item antes de continuar!`, cor_amarelo);
                            return;
                        }
                    } else {
                        if ($('#tabela-produtos tbody tr').length === 0 ||
                            $('#tabela-produtos tbody tr.vazio').length) {
                            toast(`${ic_amarelo} Insira ao menos um produto antes de continuar!`, cor_amarelo);
                            return;
                        }
                    }
                }
                const collapseTarget = $btn.data('collapse');
                if (collapseTarget) {
                    const el = document.querySelector(collapseTarget);
                    if (el) {const collapse = new bootstrap.Collapse(el, {toggle: true});}
                }
                else if (url) {
                    iniciarLoading();
                    $.post(url, function () {location.reload();}).fail(function () {alert('Erro ao tentar executar a ação.');});
                }
                else if (href) {window.location.href = href;}
                else if (acaoSelecionada === "atribuir_desconto") {
                    $('#modalDesconto').modal('show');
                }
                else if (acaoSelecionada === "atribuir_acrescimo") {
                    $('#modalAcrescimo').modal('show');
                }
                else if (acaoSelecionada === "atribuir_desconto_ped") {
                    $('#operacao').val('desconto');
                    $('#tituloModal').html('<i class="fa-solid fa-circle-minus"></i> Aplicar Desconto');
                    $('#modalDesconto').modal('show');
                }
                else if (acaoSelecionada === "atribuir_acrescimo_ped") {
                    $('#operacao').val('acrescimo');
                    $('#tituloModal').html('<i class="fa-solid fa-circle-plus"></i> Aplicar Acréscimo');
                    $('#modalDesconto').modal('show');
                }
                else if (modalTarget) {
                    const modalEl = document.querySelector(modalTarget);
                    if (modalEl) {
                        const modal = new bootstrap.Modal(modalEl);
                        modal.show();
                    }
                } else if ($btn.hasClass('btn-faturar')) {
                    const id = $btn.data('id');

                    // 🔥 tenta Pedido primeiro
                    let modalEl = document.getElementById('faturarModalP-' + id);

                    // 🔥 fallback para Orçamento
                    if (!modalEl) {
                        modalEl = document.getElementById('faturarModal-' + id);
                    }

                    const modalMenuEl = document.getElementById('menuModal' + id);

                    if (modalMenuEl) {
                        const menuInstance = bootstrap.Modal.getInstance(modalMenuEl);
                        if (menuInstance) {menuInstance.hide();}
                    }

                    if (modalEl) {
                        const modal = new bootstrap.Modal(modalEl, {
                            backdrop: 'static',
                            keyboard: false
                        });
                        modal.show();
                    }
                }
            },
            function () {
                fecharLoading();
                toast(`${ic_amarelo} ${msgNegado}`, cor_amarelo);
                $('#confirmModal').modal('show');
            }
        );
    });
    $('#tipo_desconto').change(function () {
        let tipo = $(this).val();

        $('#simbolo').text(tipo === 'valor' ? 'R$' : '%');
    });
    $(function () {
        function parseBrDate(s) {
            if (!s) return null;
            const partes = String(s).split('/');
            if (partes.length !== 3) return null;
            const d = parseInt(partes[0], 10);
            const m = parseInt(partes[1], 10);
            const y = parseInt(partes[2], 10);
            if (!d || !m || !y) return null;
            const dt = new Date(y, m - 1, d);
            return isNaN(dt.getTime()) ? null : dt;
        }
        function formatDateInput(dt) {
            if (!(dt instanceof Date) || isNaN(dt.getTime())) return '';
            const y = dt.getFullYear();
            const m = String(dt.getMonth() + 1).padStart(2, '0');
            const d = String(dt.getDate()).padStart(2, '0');
            return `${d}/${m}/${y}`;
        }
        function splitValue(total, parcelas) {
            total = parseFloat(total || 0);
            parcelas = parseInt(parcelas || 1, 10);
            if (!parcelas || parcelas <= 1) return [total.toFixed(2)];
            const base = Math.floor((total / parcelas) * 100) / 100;
            let soma = 0;
            const vals = [];
            for (let i = 0; i < parcelas - 1; i++) {
                vals.push(base.toFixed(2));
                soma += base;
            }
            vals.push((total - soma).toFixed(2));
            return vals;
        }
        function montarNumeroConta(numOrc, totalParc, parcAtual) {return `${numOrc}/${String(totalParc).padStart(2, '0')}-${String(parcAtual).padStart(2, '0')}`;}
        function parseValorEN(valor) {
            if (valor === null || valor === undefined || valor === '') return 0;
            if (typeof valor === 'number') {return isNaN(valor) ? 0 : valor;}
            let s = String(valor).trim();
            if (s.includes(',') && s.includes('.')) {
                if (s.lastIndexOf(',') > s.lastIndexOf('.')) {s = s.replace(/\./g, '').replace(',', '.');}
                else {s = s.replace(/,/g, '');}
            }
            else if (s.includes(',')) {s = s.replace(',', '.');}
            const n = parseFloat(s);
            return isNaN(n) ? 0 : n;
        }
        function formatarInputValor($input) {
            let valor = $input.val().replace(/[^\d]/g, '');
            if (!valor) {
                $input.val('0.00');
                return;
            }
            valor = (parseInt(valor, 10) / 100).toFixed(2);
            $input.val(valor);
        }
        function initDatepickerCampo($campo) {
            if (!$campo.length || $campo.hasClass('hasDatepicker')) return;
            $campo.datepicker({
                changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy",
                monthNamesShort: ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"], dayNamesMin: ["Do","2ª","3ª","4ª","5ª","6ª","Sá"],
                beforeShow: function (input) {
                    const $modal = $(input).closest('.modal-faturar-orcamento');
                    const editando = $modal.find('.btn-lib-dt-fat').attr('data-editando') === '1';
                    if (!editando) return false;
                    setTimeout(function () {$('.ui-datepicker').css('z-index', 2000);}, 0);
                }
            });
        }
        function atualizarPreviewJson(orcamentoId) {
            const $tabela = $(`#previewContasTable-${orcamentoId}`);
            const $hidden = $(`#previewContasJson-${orcamentoId}`);
            if (!$tabela.length || !$hidden.length) return;
            const dados = [];
            $tabela.find('tbody tr[data-preview-row="1"]').each(function () {
                const $tr = $(this);
                dados.push({forma_pgto_id: $tr.data('formaId'), num_conta: $tr.find('.inp-num-conta').text().trim(), valor: parseValorEN($tr.find('.inp-valor').val()).toFixed(2), data_vencimento: $tr.find('.inp-vencimento').val()});
            });
            $hidden.val(JSON.stringify(dados));
            atualizarTotalParcelas(orcamentoId);
        }
        function setEstadoBotaoDataFat($modal, editando) {
            const $campo = $modal.find('.dt-fat-orcamento');
            const $btn = $modal.find('.btn-lib-dt-fat');
            $btn.attr('data-editando', editando ? '1' : '0');
            if (editando) {
                $campo.removeAttr('readonly');
                $btn.removeClass('btn-warning').addClass('btn-success').html('<i class="fa-regular fa-circle-check"></i>');
            } else {
                $campo.attr('readonly', 'readonly');
                $btn.removeClass('btn-success').addClass('btn-warning').html('<i class="fa-regular fa-pen-to-square"></i>');
            }
        }
        function setEstadoBotaoParcela($btn, editando) {
            const $tr = $btn.closest('tr');
            const $valor = $tr.find('.inp-valor');
            const $venc = $tr.find('.inp-vencimento');
            if (editando) {
                $valor.removeAttr('readonly');
                $venc.removeAttr('readonly');
                $btn.removeClass('btn-warning').addClass('btn-success').html('<i class="fa-regular fa-circle-check"></i>');
            } else {
                $valor.attr('readonly', 'readonly');
                $venc.attr('readonly', 'readonly');
                $btn.removeClass('btn-success').addClass('btn-warning').html('<i class="fa-regular fa-pen-to-square"></i>');
            }
        }
        function gerarPreviewContas(modalEl) {
            const $modal = $(modalEl);
            const orcamentoId = $modal.data('orcamentoId');
            const numOrcamento = $modal.data('numOrcamento');
            const $tabela = $(`#previewContasTable-${orcamentoId}`);
            if (!$tabela.length) return;
            const $tbody = $tabela.find('tbody');
            const $wrap = $tabela.closest('div');
            const fatura = parseBrDate($modal.find('.dt-fat-orcamento').val()) || parseBrDate($modal.find('.dt-emi-orcamento').val());
            if (!$tbody.length || !fatura) return;
            const $linhas = $modal.find('.linha-forma-pgto').filter(function () {return parseInt($(this).data('geraParcelas') || 0, 10) === 1;});
            if (!$linhas.length) {
                $wrap.hide();
                $tbody.empty();
                atualizarPreviewJson(orcamentoId);
                return;
            }
            $wrap.show();
            let html = '';
            $linhas.each(function () {
                const $linha = $(this);
                const formaId = $linha.data('formaId');
                const valorBruto = $linha.attr('data-valor') || $linha.data('valor') || 0;
                const valor = parseValorEN(valorBruto);
                const geraParcelas = parseInt($linha.data('geraParcelas') || 0, 10) === 1;

                const parcelas = geraParcelas
                    ? parseInt($linha.data('parcelas') || 1, 10)
                    : 1;

                const intervalo = geraParcelas
                    ? parseInt($linha.data('intervalo') || 0, 10)
                    : 0;
                const valores = splitValue(valor, parcelas);
                for (let i = 1; i <= parcelas; i++) {
                    const venc = new Date(fatura);
                    venc.setDate(venc.getDate() + (intervalo * i));
                    html += `
                        <tr data-preview-row="1" data-forma-id="${formaId}">
                            <td><span class="inp-num-conta">${montarNumeroConta(numOrcamento, parcelas, i)}</span></td>
                            <td><input type="text" class="form-control form-control-sm inp-valor" value="${valores[i - 1]}" readonly></td>
                            <td><input type="text" class="form-control form-control-sm inp-vencimento" value="${formatDateInput(venc)}" readonly></td>
                            <td>
                                <button type="button" class="btn btn-warning btn-sm btn-toggle-edicao" data-editando="0" data-permissao="orcamentos.alterar_dt_venc_orc" data-msg-negado="Seu usuário não pode alterar datas de vencimento das parcelas ao faturar orçamentos!">
                                    <i class="fa-regular fa-pen-to-square"></i>
                                </button>
                            </td>
                        </tr>
                    `;
                }
            });
            $tbody.html(html);
            $tbody.find('.inp-vencimento').each(function () {initDatepickerCampo($(this));});
            atualizarPreviewJson(orcamentoId);
        }
        function atualizarTotalParcelas(orcamentoId) {
            const $tabela = $(`#previewContasTable-${orcamentoId}`);
            const $total = $(`#previewContasTotal-${orcamentoId}`);
            if (!$tabela.length || !$total.length) return;
            let soma = 0;
            $tabela.find('tbody tr[data-preview-row="1"]').each(function () {
                const valor = parseValorEN($(this).find('.inp-valor').val());
                soma += valor;
            });
            $total.text('R$ ' + formatarMoedaEN(soma));
        }
        function formatarMoedaEN(valor) {
            let num = parseFloat(valor);
            if (isNaN(num)) num = 0;
            return num.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        }
        $(document).on('input', '.inp-valor', function () {formatarInputValor($(this));});
        $(document).off('click.orcamentos', '.btn-toggle-edicao').on('click.orcamentos', '.btn-toggle-edicao', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const $btn = $(this);
            const $modal = $btn.closest('.modal-faturar-orcamento');
            const orcamentoId = $modal.data('orcamentoId');
            const permissao = $btn.data('permissao');
            const msgNegado = $btn.data('msg-negado') || 'Você não tem permissão para alterar parcelas.';
            const editando = $btn.attr('data-editando') === '1';
            verificarPermissaoAntesDeExecutar(
                permissao,
                function () {
                    setEstadoBotaoParcela($btn, !editando);
                    $btn.attr('data-editando', !editando ? '1' : '0');
                    if (editando) {atualizarPreviewJson(orcamentoId);}
                },
                function () {
                    toast(`${ic_amarelo} ${msgNegado}`, cor_amarelo);
                    $('#confirmModal').modal('show');
                }
            );
        });
        $('.modal-faturar-orcamento').off('shown.bs.modal.orcamentos').on('shown.bs.modal.orcamentos', function () {
            const $modal = $(this);
            const $campo = $modal.find('.dt-fat-orcamento');
            initDatepickerCampo($campo);
            setEstadoBotaoDataFat($modal, false);
            gerarPreviewContas(this);
        });
        $('.modal-faturar-orcamento').off('hidden.bs.modal.orcamentos').on('hidden.bs.modal.orcamentos', function () {
            const $modal = $(this);
            setEstadoBotaoDataFat($modal, false);
        });
        $(document).on('keydown', '.dt-fat-orcamento', function (e) {
            const $modal = $(this).closest('.modal-faturar-orcamento');
            const editando = $modal.find('.btn-lib-dt-fat').attr('data-editando') === '1';
            if (!editando) {
                e.preventDefault();
                return false;
            }
        });
        $(document).on('paste', '.dt-fat-orcamento', function (e) {
            const $modal = $(this).closest('.modal-faturar-orcamento');
            const editando = $modal.find('.btn-lib-dt-fat').attr('data-editando') === '1';
            if (!editando) {
                e.preventDefault();
                return false;
            }
        });
        $(document).off('click.orcamentos', '.btn-lib-dt-fat').on('click.orcamentos', '.btn-lib-dt-fat', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const $btn = $(this);
            const $modal = $btn.closest('.modal-faturar-orcamento');
            const permissao = $btn.data('permissao');
            const msgNegado = $btn.data('msg-negado') || 'Você não tem permissão para alterar data de faturamento.';
            const editando = $btn.attr('data-editando') === '1';
            verificarPermissaoAntesDeExecutar(
                permissao,
                function () {
                    setEstadoBotaoDataFat($modal, !editando);
                    if (!editando) {$modal.find('.dt-fat-orcamento').focus();}
                },
                function () {toast(`${ic_amarelo} ${msgNegado}`, cor_amarelo);}
            );
        });
        $(document).off('focus.orcamentos', '.dt-fat-orcamento').on('focus.orcamentos', '.dt-fat-orcamento', function () {$(this).data('valorAnterior', $(this).val());});
        $(document).off('change.orcamentos', '.dt-fat-orcamento').on('change.orcamentos', '.dt-fat-orcamento', function () {
            const $modal = $(this).closest('.modal-faturar-orcamento');
            const editando = $modal.find('.btn-lib-dt-fat').attr('data-editando') === '1';
            if (!editando) {
                $(this).val($(this).data('valorAnterior'));
                return;
            }
            const valorAnterior = $(this).data('valorAnterior');
            const valorAtual = $(this).val();
            if (valorAnterior === valorAtual) return;
            const modalEl = $modal[0];
            gerarPreviewContas(modalEl);
        });
        $(document).off('change.orcamentos', '.inp-valor, .inp-vencimento').on('change.orcamentos', '.inp-valor, .inp-vencimento', function () {
            const orcamentoId = $(this).closest('.modal-faturar-orcamento').data('orcamentoId');
            atualizarPreviewJson(orcamentoId);
        });
        $(document).off('click.orcamentos', '.btn-confirmar-faturamento').on('click.orcamentos', '.btn-confirmar-faturamento', function (e) {
            e.preventDefault();
            const $btn = $(this);
            const $modal = $btn.closest('.modal-faturar-orcamento');
            const orcamentoId = $btn.data('id');
            atualizarPreviewJson(orcamentoId);
            let temGateway = false;
            let formasGateway = [];
            // 🔍 percorre formas
            $modal.find('.linha-forma-pgto').each(function () {
                const $row = $(this);

                const gateway = ($row.attr('data-gateway') || '').toString().toLowerCase().trim();

                // 🔥 corrige valor BR
                let valorRaw = $row.data('valor');

                if (typeof valorRaw === 'string') {
                    valorRaw = valorRaw.replace(/\./g, '').replace(',', '.');
                }

                const valor = parseFloat(valorRaw) || 0;

                console.log("DEBUG FORMA:", {
                    gateway,
                    valor,
                    forma_id: $row.data('forma-id')
                });

                if (gateway && gateway !== 'nenhum' && gateway !== 'none') {
                    temGateway = true;

                    formasGateway.push({
                        forma_id: $row.data('forma-id'), // 🔥 padrão seguro
                        valor: valor
                    });
                }
            });
            // 🚨 NÃO tem gateway → fluxo normal
            if (!temGateway) {
                $btn.closest('form')[0].submit();
                return;
            }
            // ⚡ TEM gateway → gerar pagamento
            iniciarLoading();
            $.ajax({
                url: `/orcamentos/${orcamentoId}/gerar-pagamento/`,
                method: 'GET',
                success: function (resp) {
                    fecharLoading();
                    if (!resp.pagamentos || !resp.pagamentos.length) {
                        toast(`${ic_vermelho} Nenhum pagamento foi gerado!`, cor_vermelho);
                        return;
                    }
                    // 👉 abre modal PIX
                    abrirModalPixOrcamento(resp.pagamentos, orcamentoId);
                },
                error: function () {
                    toast(`${ic_vermelho} Erro ao gerar pagamento!`, cor_vermelho);
                }
            });
        });
        function abrirModalPixOrcamento(pagamentos, orcamentoId) {
            let html = '';
            pagamentos.forEach(p => {
                const valor = parseFloat(p.valor || 0);
                const valorFormatado = valor.toLocaleString('pt-BR', {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2
                });
                html += `
                    <div class="mb-3 text-center">
                        <img src="data:image/png;base64,${p.qr_base64}" width="220" class="mb-2">
                        <div class="input-group">
                            <input type="text" class="form-control text-center" value="${p.qr_code}" readonly>
                            <button class="btn btn-outline-secondary btn-copiar" data-code="${p.qr_code}">
                                Copiar
                            </button>
                        </div>
                        <strong class="d-block mt-2">R$ ${valorFormatado}</strong>
                    </div>
                `;
            });
            $('#pixQrContainer').html(html);
            // 🔄 reset estado
            $('#statusPix').removeClass('d-none');
            $('#statusSucesso').addClass('d-none');

            const modalPix = new bootstrap.Modal(document.getElementById('modalPixPagamento'));
            modalPix.show();

            monitorarPagamentoOrcamento(orcamentoId, modalPix);
        }
        $(document).on('click', '.btn-copiar', function () {
            const code = $(this).data('code');
            navigator.clipboard.writeText(code).then(() => {
                toast(`${ic_verde} Código PIX copiado!`, cor_verde);
            });
        });
        function monitorarPagamentoOrcamento(orcamentoId, modalPix) {
            const interval = setInterval(() => {
                $.get(`/orcamentos/${orcamentoId}/status-pagamento/`, function (resp) {
                    if (!resp.pagamentos || !resp.pagamentos.length) return;
                    // 🔥 verifica TODOS
                    const todosPagos = resp.pagamentos.every(p => {
                        const status = String(p.status).toLowerCase();
                        return ['aprovado', 'pago'].includes(status);
                    });
                    if (todosPagos) {
                        clearInterval(interval);
                        const body = document.querySelector('#modalPixPagamento .modal-body');
                        body.innerHTML = `
                            <div class="text-center py-4">
                                <div class="check-circle mx-auto">
                                    <i class="fa-solid fa-check"></i>
                                </div>
                                <h5 class="text-success fw-bold">Pagamento confirmado!</h5>
                                <p class="text-muted mb-0">Finalizando Orçamento...</p>
                            </div>
                        `;
                        toast(`${ic_verde} Pagamento aprovado!`, cor_verde);
                        // 🔥 chama faturamento automático
                        faturarOrcamentoAposPagamento(orcamentoId, modalPix);
                    }
                });
            }, 3000);
        }
        function faturarOrcamentoAposPagamento(orcamentoId, modalPix) {
            $.post(`/orcamentos/fat.orc/${orcamentoId}/`, {
                csrfmiddlewaretoken: getCSRFToken()
            })
            .done(function () {
                toast(`${ic_verde} Orçamento faturado com sucesso!`, cor_verde);
                setTimeout(() => {
                    modalPix.hide();
                    $('.modal-faturar-orcamento').modal('hide');
                    iniciarLoading();
                    setTimeout(() => {
                        window.location.href = `/orcamentos/lista/?s=${orcamentoId}&sit=Faturado`;
                    }, 1500);
                }, 1500);
            })
            .fail(function () {
                toast(`${ic_vermelho} Erro ao faturar orçamento!`, cor_vermelho);
            });
        }
    });
    // Teste para Faturamento de Pedidos
    function formatarMoedaBrasileira(valor) {
        return parseValor(valor).toFixed(2);
    }
    $(function () {
        function initDatepickerCampo($campo) {
            if (!$campo.length || $campo.hasClass('hasDatepicker')) return;
            $campo.datepicker({
                changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy", monthNamesShort: ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"], dayNamesMin: ["Do","2ª","3ª","4ª","5ª","6ª","Sá"],
                beforeShow: function (input) {
                    const $modal = $(input).closest('.modal-faturar-pedido');
                    const editando = $modal.find('.btn-lib-dt-fat-ped').attr('data-editando') === '1';
                    if (!editando) return false;
                    setTimeout(function () {$('.ui-datepicker').css('z-index', 2000);}, 0);
                }
            });
        }
        function parseDataBR(dataStr) {
            if (!dataStr) return new Date();
            const partes = dataStr.split('/');
            if (partes.length !== 3) return new Date();
            return new Date(parseInt(partes[2]), parseInt(partes[1]) - 1, parseInt(partes[0]));
        }
        function splitValue(total, parcelas) {
            const base = Math.floor((total / parcelas) * 100) / 100;
            let soma = 0, arr = [];
            for (let i = 0; i < parcelas - 1; i++) {
                arr.push(base.toFixed(2));
                soma += base;
            }
            arr.push((total - soma).toFixed(2));
            return arr;
        }
        function formatDate(dt) {
            return dt.toLocaleDateString('pt-BR');
        }
        function gerarParcelas($modal) {
            const $tbody = $modal.find('.preview-table tbody');
            const pedidoId = $modal.data('pedidoId');
            $tbody.empty();
            let temParcelas = false;
            const dataBaseStr = $modal.find('.dt-fat-pedido').val();
            const dataBase = parseDataBR(dataBaseStr);
            $modal.find('#tableFormas-' + pedidoId + ' tbody tr').each(function () {
                const parcelas = parseInt($(this).data('parcelas'));
                const dias = parseInt($(this).data('dias'));
                const valor = parseValor($(this).data('valor'));
                if (parcelas <= 1 || $(this).data('gera') != 1) return;
                temParcelas = true;
                const valores = splitValue(valor, parcelas);
                for (let i = 1; i <= parcelas; i++) {
                    let dt = new Date(dataBase);
                    dt.setDate(dt.getDate() + (dias * i));
                    $tbody.append(`
                        <tr>
                            <td>${pedidoId}/${parcelas}-${i}</td>
                            <td><input class="form-control form-control-sm inp-valor" value="${valores[i-1]}" readonly></td>
                            <td><input class="form-control form-control-sm inp-vencimento" value="${formatDate(dt)}" readonly></td>
                            <td>
                                <button class="btn btn-warning btn-sm btn-edit-parcela" data-editando="0"><i class="fa fa-pen"></i></button>
                            </td>
                        </tr>
                    `);
                }
            });
            if (temParcelas) {
                $modal.find('.preview-table, .preview-title').removeClass('d-none');
            } else {
                $modal.find('.preview-table, .preview-title').addClass('d-none');
            }
        }
        $(document).on('change', '.dt-fat-pedido', function () {
            const $modal = $(this).closest('.modal');
            gerarParcelas($modal);
        });
        // MOSTRA CAMPOS PARCELA
        $(document).on('change', '[id^=formaPgtoSelect-]', function () {
            const $select = $(this);
            const id = $select.val();
            const $modal = $select.closest('.modal');
            if (!id) return;
            $.get('/formas_pgto/forma-pgto-info/' + id + '/', function (data) {
                $modal.find('.campos-parcela').toggleClass('d-none', !data.gera_parcelas);
                if (!data.gera_parcelas) {
                    $modal.find('[id^=parcelasPgto-]').val(1);
                    $modal.find('[id^=diasPgto-]').val(30);
                }
                $select.data('gateway', data.gateway || 'nenhum');
                $select.data('credencial', data.credenciais || null);
                $select.data('troco', data.troco ? 1 : 0);
                $select.data('gera', data.gera_parcelas ? 1 : 0);
            });
        });
        // ADD FORMA
        $(document).on('click', '.btn-add-forma', function () {
            const $modal = $(this).closest('.modal');
            const pedidoId = $modal.data('pedidoId');
            const select = $modal.find('#formaPgtoSelect-' + pedidoId);
            const formaId = select.val();
            const formaDesc = select.find('option:selected').text();
            const valor = $modal.find('#valorPgto-' + pedidoId).val();
            let valorNum = parseValor(valor);
            const parcelas = $modal.find('#parcelasPgto-' + pedidoId).val() || 1;
            const dias = $modal.find('#diasPgto-' + pedidoId).val() || 0;
            const geraParcelas = select.data('gera') == 1;
            const permiteTroco = select.data('troco') == 1;
            const parcelasTxt = geraParcelas ? parcelas : '-';
            const diasTxt     = geraParcelas ? dias : '-';
            const gateway = select.data('gateway') || 'nenhum';
            const credencial = select.data('credencial');
            const accessToken = credencial?.access_token;
            if (!formaId || !valor) {
                alert('Informe forma e valor');
                return;
            }
            if (select.data('troco') === undefined) {
                toast(`${ic_amarelo} Aguarde carregar dados da forma`, cor_amarelo);
                return;
            }
            if (select.data('gateway') === undefined) {
                toast('Aguarde carregar os dados da forma...', 'warning');
                return;
            }
            if (valorNum <= 0) {
                alert('Valor inválido');
                return;
            }
            const $tbody = $modal.find('#tableFormas-' + pedidoId + ' tbody');
            const jaExiste = $tbody.find('tr').filter(function () {return $(this).data('forma') == formaId;}).length > 0;
            if (jaExiste) {
                toast(`${ic_amarelo} Forma de pagamento já adicionada!`, cor_amarelo);
                return;
            }
            const index = $tbody.children().length + 1;
            $tbody.append(`
                <tr data-forma="${formaId}" data-valor="${valorNum}" data-parcelas="${geraParcelas ? parcelas : 1}" data-dias="${geraParcelas ? dias : 0}" data-gera="${geraParcelas ? 1 : 0}" data-troco="${permiteTroco ? 1 : 0}" data-gateway="${gateway}" data-credencial='${JSON.stringify(credencial)}'>
                    <td>${index}</td>
                    <td>${formaDesc}</td>
                    <td>${valorNum.toFixed(2)}</td>
                    <td>${parcelasTxt}</td>
                    <td>${diasTxt}</td>
                    <td>
                        <button class="btn btn-danger btn-sm btn-remove-forma"><i class="fa fa-trash"></i></button>
                    </td>
                </tr>
            `);
            gerarParcelas($modal);
            calcularTroco($modal);
            select.val(null).trigger('change');
            select.select2('open');
            const saldo = getTotalPedido($modal) - getTotalFormas($modal);
            $modal.find('#valorPgto-' + pedidoId).val(saldo > 0 ? saldo.toFixed(2) : '0.00');
            $modal.find('#parcelasPgto-' + pedidoId).val(1);
            $modal.find('#diasPgto-' + pedidoId).val(30);
            $modal.find('.campos-parcela').addClass('d-none');
            atualizarSaldo($modal);
        });
        $(document).on('click', '.btn-confirmar-pedido', function () {
            const $modal = $(this).closest('.modal');
            const pedidoId = $modal.data('pedidoId');
            let formas = [];
            let parcelas = [];
            $modal.find('#tableFormas-' + pedidoId + ' tbody tr').each(function () {
                formas.push({forma: $(this).data('forma'), valor: $(this).data('valor'), parcelas: $(this).data('parcelas'), dias: $(this).data('dias')});
            });
            $modal.find('#previewPedido-' + pedidoId + ' tbody tr').each(function () {
                parcelas.push({numero: $(this).find('td:eq(0)').text(), valor: $(this).find('td:eq(1)').text(), vencimento: $(this).find('td:eq(2)').text()});
            });
            $modal.find('#dadosPagamento-' + pedidoId).val(JSON.stringify(formas));
            $modal.find('#parcelasJson-' + pedidoId).val(JSON.stringify(parcelas));
        });
        $(document).on('click', '.btn-remove-forma', function () {
            const $modal = $(this).closest('.modal');
            const pedidoId = $modal.data('pedidoId');
            $(this).closest('tr').remove();
            $modal.find('#tableFormas-' + pedidoId + ' tbody tr').each(function (i) {
                $(this).find('td:first').text(i + 1);
            });
            gerarParcelas($modal);
            calcularTroco($modal);
            const saldo = getTotalPedido($modal) - getTotalFormas($modal);
            $modal.find('#valorPgto-' + pedidoId).val(saldo > 0 ? saldo.toFixed(2) : '0.00');
            atualizarSaldo($modal);
        });
        $(document).on('click', '.btn-canc-fat-pedido', function () {
            const $modal = $(this).closest('.modal');
            const pedidoId = $modal.data('pedidoId');
            $modal.find('#tableFormas-' + pedidoId + ' tbody').empty();
            $modal.find('#previewPedido-' + pedidoId + ' tbody').empty();
            $modal.find('#valorPgto-' + pedidoId).val('0.00');
            $modal.find('input, textarea').not('[type=hidden]').val('');
            // 🔄 recalcula tudo
            gerarParcelas($modal);
            calcularTroco($modal);
            atualizarSaldo($modal);
        });
        $(document).on('input', '[id^=valorPgto-]', function () {
            atualizarSaldo($(this).closest('.modal'));
        });
        $(document).on('click', '.btn-edit-parcela', function () {
            const $btn = $(this);
            const $tr = $btn.closest('tr');
            const editando = $btn.attr('data-editando') === '1';
            const $valor = $tr.find('.inp-valor');
            const $venc = $tr.find('.inp-vencimento');
            if (!editando) {
                $valor.removeAttr('readonly');
                $venc.removeAttr('readonly');
                $btn.removeClass('btn-warning').addClass('btn-success').html('<i class="fa fa-check"></i>').attr('data-editando', '1');
            } else {
                $valor.attr('readonly', true);
                $venc.attr('readonly', true);
                $btn.removeClass('btn-success').addClass('btn-warning').html('<i class="fa fa-pen"></i>').attr('data-editando', '0');
            }
        });
        function calcularTroco($modal) {
            const pedidoId = $modal.data('pedidoId');
            let totalFormas = 0;
            let permiteTroco = false;
            $modal.find('#tableFormas-' + pedidoId + ' tbody tr').each(function () {
                totalFormas += parseValor($(this).data('valor') || 0);
                if ($(this).data('troco') == 1) {
                    permiteTroco = true;
                }
            });
            const totalPedido = getTotalPedido($modal);
            let troco = 0;
            if (permiteTroco && totalFormas > totalPedido) {
                troco = totalFormas - totalPedido;
            }
            const $campoTroco = $modal.find('#troco-' + pedidoId);
            const $container = $campoTroco.closest('.col-md-2');
            if (troco > 0) {
                $campoTroco.val(troco.toFixed(2));
                $container.removeClass('d-none'); // mostra
            } else {
                $campoTroco.val('0.00');
                $container.addClass('d-none'); // esconde
            }
        }
        function setEstadoBotaoDataFatPedido($modal, editando) {
            const $input = $modal.find('.dt-fat-pedido');
            const $btn = $modal.find('.btn-lib-dt-fat-ped');
            if (editando) {
                $input.prop('readonly', false);
                $btn.removeClass('btn-outline-secondary').addClass('btn-success').html('<i class="fa fa-check"></i>').attr('data-editando', '1');
            } else {
                $input.prop('readonly', true);
                $btn.removeClass('btn-success').addClass('btn-outline-secondary').html('<i class="fa fa-pen"></i>').attr('data-editando', '0');
            }
        }
        $(document).off('click.pedidos', '.btn-lib-dt-fat-ped').on('click.pedidos', '.btn-lib-dt-fat-ped', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const $btn = $(this);
            const $modal = $btn.closest('.modal-faturar-pedido');
            const permissao = $btn.data('permissao');
            const msgNegado = $btn.data('msg-negado');
            const editando = $btn.attr('data-editando') === '1';
            verificarPermissaoAntesDeExecutar(
                permissao,
                function () {
                    setEstadoBotaoDataFatPedido($modal, !editando);
                    if (!editando) {
                        $modal.find('.dt-fat-pedido').focus();
                    } else {
                        gerarParcelas($modal);
                    }
                },
                function () {
                    toast(`${ic_amarelo} ${msgNegado}`, cor_amarelo);
                }
            );
        });
        $('.modal-faturar-pedido').off('shown.bs.modal.pedidos').on('shown.bs.modal.pedidos', function () {
            const $modal = $(this);
            const pedidoId = $modal.data('pedidoId');

            initDatepickerCampo($modal.find('.dt-fat-pedido'));
            setEstadoBotaoDataFatPedido($modal, false);

            // 🔥 PEGA O TOTAL DIRETO DO data-total DO MODAL
            const totalRaw = $modal.attr('data-total');

            // 🔥 CONVERTE CORRETAMENTE (preserva centavos)
            let totalNumerico;
            if (typeof totalRaw === 'string') {
                // Remove espaços e substitui vírgula por ponto
                totalNumerico = parseFloat(totalRaw.replace(',', '.').trim());
            } else {
                totalNumerico = parseFloat(totalRaw);
            }

            // Se não for número válido, usa 0
            if (isNaN(totalNumerico)) {
                totalNumerico = 0;
            }

            // Salva no data() do modal
            $modal.data('total', totalNumerico);

            // 🔥 PREENCHE O CAMPO VALOR COM O TOTAL CORRETO
            const $campoValor = $modal.find('#valorPgto-' + pedidoId);
            $campoValor.val(totalNumerico.toFixed(2));

            gerarParcelas($modal);
            atualizarSaldo($modal);
        });
        function getTotalPedido($modal) {
            const total = $modal.data('total');

            // Se já tem no data(), retorna
            if (total !== undefined && total !== null && !isNaN(total)) {
                return parseFloat(total);
            }

            // Caso contrário, pega do atributo data-total
            const totalRaw = $modal.attr('data-total');
            let totalNumerico;

            if (typeof totalRaw === 'string') {
                totalNumerico = parseFloat(totalRaw.replace(',', '.').trim());
            } else {
                totalNumerico = parseFloat(totalRaw);
            }

            return isNaN(totalNumerico) ? 0 : totalNumerico;
        }
        function getTotalFormas($modal) {
            let soma = 0;
            $modal.find('#tableFormas-' + $modal.data('pedidoId') + ' tbody tr').each(function () {
                soma += parseValor($(this).data('valor'));
            });
            return soma;
        }
        function atualizarSaldo($modal) {
            const pedidoId = $modal.data('pedidoId');
            const totalPedido = getTotalPedido($modal);
            const totalFormas = getTotalFormas($modal);
            const saldo = totalPedido - totalFormas;
            const $input = $modal.find('#valorPgto-' + pedidoId);
            const $saldo = $modal.find('.saldo-restante');
            console.log('TOTAL:', totalPedido);
            console.log('FORMAS:', totalFormas);
            console.log('SALDO:', saldo);
            $input.removeClass('border-success border-danger');
            if (saldo === 0) {
                $input.addClass('border-success');
            } else if (saldo < 0) {
                $input.addClass('border-danger');
            }
            if ($saldo.length) {
                $saldo.text('Saldo Restante: R$ ' + formatarMoedaBrasileira(saldo));
            }
        }
        $(document).on('focus', '[id^=valorPgto-]', function () {
            const $modal = $(this).closest('.modal');
            const saldo = getTotalPedido($modal) - getTotalFormas($modal);
            if (parseValor($(this).val()) === 0 || !$(this).val()) {
                $(this).val(saldo.toFixed(2));
            }
        });
    });
    $(document).on('click', '.btn-confirmar-pedido', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const $modal = $(this).closest('.modal');
        const pedidoId = $modal.data('pedidoId');
        let formasNormais = [];
        let formasGateway = [];
        let parcelas = [];
        $modal.find('#tableFormas-' + pedidoId + ' tbody tr').each(function () {
            const gateway = $(this).data('gateway');
            const valor = parseValor($(this).data('valor') || 0);
            if (valor <= 0) return;
            const obj = {
                forma: $(this).data('forma'),
                valor: valor,
                parcelas: parseInt($(this).data('parcelas') || 1),
                dias: parseInt($(this).data('dias') || 0)
            };
            if (gateway && gateway !== 'nenhum') {
                formasGateway.push(obj);
            } else {
                formasNormais.push(obj);
            }
        });
        $modal.find('#previewPedido-' + pedidoId + ' tbody tr').each(function () {
            parcelas.push({
                numero: $(this).find('td:eq(0)').text(),
                valor: $(this).find('td:eq(1) input').val(),
                vencimento: $(this).find('td:eq(2) input').val()
            });
        });
        if (formasNormais.length > 0) {
            faturarNormal($modal, pedidoId, formasNormais, parcelas);
        }
        if (formasGateway.length > 0) {
            $.get(`/pedidos/${pedidoId}/recuperar-pagamento/`, function (resp) {
                if (!resp.erro && resp.qr_code) {
                    toast(`${ic_amarelo} Existe um PIX pendente para este pedido`, cor_amarelo);
                    abrirModalPix([resp], pedidoId);
                } else {
                    gerarPix($modal, pedidoId, formasGateway);
                }
            }).fail(function () {
                gerarPix($modal, pedidoId, formasGateway);
            });
        }
    });
    function faturarNormal($modal, pedidoId, formas, parcelas) {
        iniciarLoading();

        $.post(`/pedidos/faturar/${pedidoId}/`, {
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(),
            dados_pagamento: JSON.stringify(formas),
            parcelas_json: JSON.stringify(parcelas)
        }, function (resp) {
            if (resp.ok) {
                toast(`${ic_verde} ${resp.msg}`, cor_verde);
            } else {
                alert(resp.msg || 'Erro ao faturar');
            }
        }).always(function () {
            fecharLoading();
        });
    }
    function gerarPix($modal, pedidoId, formas) {
        iniciarLoading();
        $.post(`/pedidos/${pedidoId}/gerar-pagamento/`, {
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(),
            formas: JSON.stringify(formas)
        }, function (resp) {
            fecharLoading();
            if (resp.pagamentos && resp.pagamentos.length > 0) {
                abrirModalPix(resp.pagamentos, pedidoId);
            } else {
                alert('Erro ao gerar PIX');
            }
        });
    }
    function abrirModalPix(pagamentos, pedidoId) {
        let html = '';
        pagamentos.forEach(p => {
            const valorFormatado = parseFloat(p.valor).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
            html += `
                <div class="mb-3">
                    <img src="data:image/png;base64,${p.qr_base64}" width="220" class="mb-2">
                    <div class="input-group">
                        <input type="text" class="form-control text-center" value="${p.qr_code}" readonly>
                        <button class="btn btn-outline-secondary btn-copiar" data-code="${p.qr_code}">Copiar</button>
                    </div>
                    <strong class="d-block mt-2">R$ ${valorFormatado}</strong>
                </div>
            `;
        });
        $('#pixQrContainer').html(html);
        $('#statusPix').removeClass('d-none');
        $('#statusSucesso').addClass('d-none');
        const modalPix = new bootstrap.Modal(document.getElementById('modalPixPagamento'));
        modalPix.show();
        monitorarPagamento(pedidoId, modalPix);
    }
    $(document).on('click', '.btn-copiar', function () {
        const code = $(this).data('code');
        navigator.clipboard.writeText(code);
        $(this).text('Copiado!');
        setTimeout(() => {
            $(this).text('Copiar');
        }, 2000);
    });
    function monitorarPagamento(pedidoId, modalPix) {
        const interval = setInterval(() => {
            $.get(`/pedidos/${pedidoId}/status-pagamento/`, function (resp) {
                if (resp.status === 'pago') {
                    clearInterval(interval);
                    const body = document.querySelector('#modalPixPagamento .modal-body');
                    body.innerHTML = `
                        <div class="text-center py-4">
                            <div class="check-circle mx-auto">
                                <i class="fa-solid fa-check"></i>
                            </div>
                            <h5 class="text-success fw-bold">Pagamento confirmado!</h5>
                            <p class="text-muted mb-0">Finalizando Venda...</p>
                        </div>
                    `;
                    toast(`${ic_verde} Pedido faturado com sucesso!`, cor_verde);
                    setTimeout(() => {
                        modalPix.hide();
                        $('.modal-faturar-pedido').modal('hide');
                        iniciarLoading();
                        setTimeout(() => {
                            window.location.href = `/pedidos/lista/?s=${pedidoId}&sit=Faturado`;
                        }, 3000);
                    }, 2000);
                }
            });
        }, 3000);
    }
    const msg = sessionStorage.getItem('msg_sucesso');
    if (msg) {
        toast(`${ic_verde} ${msg}`, cor_verde);
        sessionStorage.removeItem('msg_sucesso');
    }
    $(document).on('click', '.btn-abrir-modal-cancelamento', function () {
        const id = $(this).data('orcamento-id');
        const motivo = $(`#motivoCancelamento${id}`).val().trim();
        const modalTarget = $(this).data('bs-target');
        if (!motivo) {
            toast(`${ic_amarelo} Informe o motivo do cancelamento!`, cor_amarelo);
            $(`#motivoCancelamento${id}`).focus();
            return;
        }
        const modalEl = document.querySelector(modalTarget);
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    });
    $(document).on('click', '.btn-confirmar-cancelamento', function () {
        const id = $(this).data('orcamento-id');
        const motivo = $(`#motivoCancelamento${id}`).val().trim();
        if (!motivo) {
            toast(`${ic_amarelo} Informe o motivo do cancelamento!`, cor_amarelo);
            return;
        }
        $.ajax({
            url: `/orcamentos/canc.orc/${id}/`, type: 'POST', data: {motivo: motivo,  csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').first().val()},
            success: function () {
                toast(`${ic_verde} Orçamento cancelado com sucesso!`, cor_verde);
                iniciarLoading();
                setTimeout(() => location.reload(), 3000);
            },
            error: function () {toast(`${ic_vermelho} Erro ao cancelar orçamento!`, cor_vermelho);}
        });
    });
    // Pedidos
    $(document).on('click', '.btn-abrir-modal-pedido', function () {
        const id = $(this).data('orcamento-id');
        const motivo = $(`#motivoCancelamento${id}`).val().trim();
        const modalTarget = $(this).data('bs-target');
        if (!motivo) {
            toast(`${ic_amarelo} Informe o motivo do pedido!`, cor_amarelo);
            $(`#motivoCancelamento${id}`).focus();
            return;
        }
        const modalEl = document.querySelector(modalTarget);
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    });
    $(document).on('click', '.btn-confirmar-canc-pedido', function () {
        const id = $(this).data('orcamento-id');
        const motivo = $(`#motivoCancelamento${id}`).val();
        if (!motivo) {
            toast(`${ic_amarelo} Informe o motivo do pedido!`, cor_amarelo);
            return;
        }
        $.ajax({
            url: `/pedidos/cancelar/${id}/`, type: 'POST', data: {motivo: motivo,  csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').first().val()},
            success: function () {
                toast(`${ic_verde} Pedido cancelado com sucesso!`, cor_verde);
                iniciarLoading();
                setInterval(location.reload, 3000);
            },
            error: function () {toast(`${ic_vermelho} Erro ao cancelar pedido!`, cor_vermelho);}
        });
    });
    // Contador de confirmação
    $('.modal').on('shown.bs.modal', function () {
        const modal = $(this);
        const btn = modal.find('.btn-confirmar');
        const contadorSpan = btn.find('.contador');
        let count = 3;
        btn.prop('disabled', true);
        contadorSpan.text(count).show();
        const intervalo = setInterval(function () {
            count--;
            if (count <= 0) {
                clearInterval(intervalo);
                btn.prop('disabled', false);
                contadorSpan.hide(); // só esconde
            }
            else {contadorSpan.text(count);}
        }, 1000);
        modal.data('intervalo', intervalo);
    });
    $('.modal').on('hidden.bs.modal', function () {
        const modal = $(this);
        const intervalo = modal.data('intervalo');
        if (intervalo) {
            clearInterval(intervalo);
            modal.removeData('intervalo');
        }
        const btn = modal.find('.btn-confirmar');
        const contadorSpan = btn.find('.contador');
        btn.prop('disabled', true);
        contadorSpan.text(3).show();
    });
    // Verificador de Parcelas Máximas
    let verificando = false;
    $("#id_parcelas").on("blur", function(){
        if(verificando) return;
        let parcelas = $(this).val();
        if(parcelas == "" || parcelas <= 0)
            return;
        verificando = true;
        $.ajax({
            url: "/ajax/verificar-parcelas/", type: "GET", data: {parcelas: parcelas},
            success: function(data){
                if(!data.permitido){
                    toast(`${ic_info} Quantidade de parcelas superior ao Permitido na Filial! Máximo: ${data.maximo} parcelas.`, cor_info);
                    $("#id_parcelas").val(data.maximo);
                    $("#id_parcelas").focus();
                }
                verificando = false;
            },
            error: function(){verificando = false;}
        });
    });
    $("#id_dias").on("blur", function(){
        if(verificando) return;
        let dias = $(this).val();
        if(dias == "" || dias <= 0)
            return;
        verificando = true;
        $.ajax({
            url: "/ajax/verificar-parcelas/", type: "GET", data: {dias: dias},
            success: function(data){
                if(!data.permitido){
                    toast(`${ic_info} Quantidade de dias superior ao Permitido na Filial! Máximo: ${data.maximo} dias.`, cor_info);
                    $("#id_dias").val(data.maximo);
                    $("#id_dias").focus();
                }
                verificando = false;
            },
            error: function(){verificando = false;}
        });
    });
    // GET em Formas PGTO
    $('#id_formas_pgto').change(function(){
        let id = $(this).val();
        if(!id) return;
        $.get('/formas_pgto/forma-pgto-info/' + id + '/', function(data){
            if(data.gera_parcelas){
                $('#div_id_parcelas').show();
                $('#div_id_dias').show();
            }else{
                $('#div_id_parcelas').hide();
                $('#div_id_dias').hide();
                $('#id_parcelas').val(1);
                $('#id_dias').val(30);
            }
        });
    });
    // Para Pedidos
    let verificandoPedido = false;

    // PARCELAS
    $(document).on('blur', '[id^=parcelasPgto-]', function () {
        if (verificandoPedido) return;

        const $input = $(this);
        const parcelas = parseInt($input.val());

        if (!parcelas || parcelas <= 0) return;

        verificandoPedido = true;

        $.ajax({
            url: "/ajax/verificar-parcelas/",
            type: "GET",
            data: { parcelas: parcelas },

            success: function (data) {
                if (!data.permitido) {
                    toast(`${ic_info} Máximo permitido: ${data.maximo} parcelas.`, cor_info);
                    $input.val(data.maximo);
                    $input.focus();
                }
                verificandoPedido = false;
            },
            error: function () {
                verificandoPedido = false;
            }
        });
    });
    // DIAS
    $(document).on('blur', '[id^=diasPgto-]', function () {
        if (verificandoPedido) return;

        const $input = $(this);
        const dias = parseInt($input.val());

        if (!dias || dias <= 0) return;

        verificandoPedido = true;

        $.ajax({
            url: "/ajax/verificar-parcelas/",
            type: "GET",
            data: { dias: dias },

            success: function (data) {
                if (!data.permitido) {
                    toast(`${ic_info} Máximo permitido: ${data.maximo} dias.`, cor_info);
                    $input.val(data.maximo);
                    $input.focus();
                }
                verificandoPedido = false;
            },
            error: function () {
                verificandoPedido = false;
            }
        });
    });
    // Teste
    if ($('#id_desconto, #id_acrescimo, #total-frete') === "") {$('#id_desconto, #id_acrescimo, #total-frete').val("0.00");}
    function addDtInterv(dataString, intervalo) {
        const [dia, mes, ano] = dataString.split('/').map(Number);
        const data = new Date(ano, mes - 1, dia);
        data.setDate(data.getDate() + Number(intervalo));
        const novoDia = data.getDate().toString().padStart(2, '0');
        const novoMes = (data.getMonth() + 1).toString().padStart(2, '0');
        const novoAno = data.getFullYear();
        return `${novoDia}/${novoMes}/${novoAno}`;
    }
    let toastErrorShown = false;
    function parseDecimalAlt(v) {
        return parseFloat(String(v || '0').replace(',', '.')) || 0;
    }
    function atualizarAltCorte($campoAlt) {
        const porta = $campoAlt.data('porta');
        const alt = parseDecimalAlt($campoAlt.val());
        const altCorte = (Math.round(alt * 100) + 5) / 100;
        $(`.alt-corte[data-porta="${porta}"]`).val(altCorte.toFixed(2));
        console.log('ALT FINAL:', alt, 'ALT CORTE:', altCorte);
    }
    function iniciarLoading() {
        $('#loadingOverlay').prop('hidden', false);
        requestAnimationFrame(() => {
            $('#loadingOverlay').addClass('show');
        });
    }
    let loadingTimeout = null;
    function finalizarLoading() {
        if (loadingTimeout) {clearTimeout(loadingTimeout);}
        loadingTimeout = setTimeout(() => {
            fecharLoading();
            loadingTimeout = null;
        }, 2500);
    }
    function fecharLoading() {
        $('#loadingOverlay').removeClass('show');
        setTimeout(() => {
            $('#loadingOverlay').prop('hidden', true);
        }, 250);
    }
    function arredondarParaCima(valor, casasDecimais) {
        let fator = Math.pow(10, casasDecimais);
        return (Math.ceil(valor * fator) / fator).toFixed(casasDecimais);
    }
    function arredondarComAjuste(valor) {
        let arredondado = parseFloat(valor.toFixed(2));
        let decimal = arredondado % 1;
        if (decimal >= 0.480 && decimal < 0.495) {arredondado = Math.floor(arredondado) + 0.50;}
        return arredondado.toFixed(2);
    }
    function arredondarInteiro(valor) {
        let num = parseFloat(valor);
        if (isNaN(num)) return "";
        let inteiro = Math.floor(num);            // parte inteira
        let decimal = num - inteiro;              // parte decimal
        if (decimal > 0.50) {return inteiro + 1;}
        else {return inteiro;}
    }
    function calcFtPeso(porta) {
        let alt_corte = parseFloat($(`.alt-corte[data-porta="${porta}"]`).val().replace(',', '.'));
        let m2 = parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;
        if (isNaN(alt_corte)) {
            $(`.ft-peso[data-porta="${porta}"]`).val('');
            return;
        }
        let filialId = $('#id_vinc_fil').val();
        let multi = DADOS_FILIAL?.[filialId]?.multi_m2;
        if (!multi) multi = 15;
        let resultado = m2 * parseFloat(multi);
        $(`.ft-peso[data-porta="${porta}"]`).val(resultado.toFixed(2));
    }
    function calcLgCorte(porta) {
        let largRaw = $(`.larg[data-porta="${porta}"]`).val();
        if (!largRaw) return "";
        let larg = parseFloat(largRaw.replace(/,/g, ""));
        if (isNaN(larg)) return "";
        const tp_vao = $(`.tipo-vao[data-porta="${porta}"]`).val();
        let calc = 0;
        if (tp_vao === "Fora do Vão") {calc = larg + 0.10;}
        else if (tp_vao === "Dentro do Vão") {calc = larg - 0.08;}
        else if (tp_vao === '1 Lado Dentro do Vão') {calc = larg + 0.03;}
        $(`.larg-corte[data-porta="${porta}"]`).val(calc.toFixed(2));
    }
    function calcPeso(porta) {
        let alt_corte = parseFloat($(`.alt-corte[data-porta="${porta}"]`).val().replace(',', '.'));
        let m2 = parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;
        if (isNaN(alt_corte)) {
            $(`.ft-peso[data-porta="${porta}"]`).val('');
            return;
        }
        let filialId = $('#id_vinc_fil').val();
        let multi = DADOS_FILIAL?.[filialId]?.multi_m2;
        if (!multi) multi = 15;
        let resultado = m2 * parseFloat(multi);
        $(`.peso[data-porta="${porta}"]`).val(resultado.toFixed(2));
    }
    function calcularEixoMotor(porta) {
        let ft_peso = parseFloat($(`.ft-peso[data-porta="${porta}"]`).val());
        let larg_corte = parseFloat($(`.larg-corte[data-porta="${porta}"]`).val());
        let qtd = 1;
        if (isNaN(ft_peso) || isNaN(larg_corte) || isNaN(qtd)) {
            $(`.eix-mot[data-porta="${porta}"]`).val('');
            return;
        }
        let calc = (((larg_corte * 0.8) * ft_peso) * (1.5 * qtd));
        let final = arredondarParaCima(calc, 0);
        $(`.eix-mot[data-porta="${porta}"]`).val(final);
    }
    function calcM2(porta) {
        let larg_corte = parseFloat($(`.larg-corte[data-porta="${porta}"]`).val()) || 0;
        let alt_corte  = parseFloat($(`.alt-corte[data-porta="${porta}"]`).val()) || 0;
        let rolo       = parseFloat($(`.rolo[data-porta="${porta}"]`).val()) || 0;
        let calc = (rolo + alt_corte) * larg_corte;
        let aux = arredondarComAjuste(calc);
        $(`.m2[data-porta="${porta}"]`).val(aux);
    }
    function calcQtdLam(porta) {
        let alt_corte = parseFloat($(`.alt-corte[data-porta="${porta}"]`).val());
        let rolo = parseFloat($(`.rolo[data-porta="${porta}"]`).val());
        let calc = (alt_corte + rolo) / 0.075;
        let aux = arredondarInteiro(calc);
        $(`.qtd-laminas[data-porta="${porta}"]`).val(aux);
    }
    function resetarControleRegras() {motorCtrl = {};}
    toastErrorShown = false;
    $(document).on("change", ".tipo-lamina", async function () {
        iniciarLoading();
        const porta = $(this).data("porta");
        await carregarProdutosIniciais(porta);
        await atualizarSubtotal();
        finalizarLoading();
    });
    $(document).on('keyup change', '.larg', function () {
        let porta = $(this).data('porta');
        calcLgCorte(porta);
    });
    $(document).on('change', '.tipo-vao', async function () {
        iniciarLoading();
        const tabelas = $('[id^="tblProd_"]');
        for (const el of tabelas) {
            const porta = el.id.split('_')[1];
            calcLgCorte(porta);
            calcM2(porta);
            calcFtPeso(porta);
            calcPeso(porta);
            calcularEixoMotor(porta);
            calcQtdLam(porta);
            await carregarProdutosIniciais(porta);
            await new Promise(resolve => setTimeout(resolve, 100));
            recalcularTotaisPorta(porta);
        }
        atualizarJSONPortas();
        gerarJSONFormas();
        finalizarLoading();
        atualizarSubtotal();
    });
    $("#prod_servBtn, #adicionaisBtn, #form_pgtoBtn").on("click", async function () {
        await atualizarSubtotal();
        calcularValorForma();
        somaFormas();
        atualizarJSONPortas();
        gerarJSONFormas();
    });
    $(document).on('change', '#id_pintura, #id_tp_pintura', async function () {
        iniciarLoading();
        const tabelas = $('[id^="tblAdc_"]');
        for (const el of tabelas) {
            const porta = el.id.split('_')[1];
            const adicionais = prodAdcManager.data[porta] || [];
            prodAdcManager.data[porta] = adicionais.filter(item => {
                const regra = item.regra_origem || '';
                const isPintura = regra.includes('PINTURA');
                if (isPintura) {
                    $(`#tblAdc_${porta} tbody tr[data-item-id="${item.id}"]`).remove();
                    return false;
                }
                return true;
            });
            await carregarProdutosIniciais(porta);
        }
        await atualizarSubtotal();
        finalizarLoading();
    });
    gerarJSONFormas();
    let debounceTimeout;
    function atualizarCalculoCompletoDebounced() {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {calcFtPeso();}, 200);
    }
    $('#id_alt, #id_tp_vao, #id_larg, #id_qtd, #id_rolo, #id_alt_corte, #id_larg_corte').on('blur', atualizarCalculoCompletoDebounced);
    $('#desconto, #acrescimo').mask('000.000.000.000.000,00', {reverse: true});
    $('#id_vl_prod, #id_vl_prod_adc, #editValorItemInput, #editValorItemAdcInput, .editable, .inpFrete, #id_desconto, #id_acrescimo').mask('00000.00', {reverse: true});
    $('#editQtdInput, #editQtdAdcInput, #id_qtd_prod, #id_qtd_prod_adc').mask('000,000.00', {reverse: true});
    $('#id_vl_p_s, #id_vl_compra').mask('000000000.00', {reverse: true});
    var desconto = 0;
    var total = 0;
    function atualizarSubtotal() {
        return new Promise(resolve => {
            let subtotal   = 0;
            let custoTotal = 0;
            let vl_p_s = parseValor($('#id_vl_p_s').val());
            $('[id^="tblProd_"] tbody tr, [id^="tblAdc_"] tbody tr').each(function () {
                const compraTxt = $(this).find('.tot-compra').text().trim();
                const vendaTxt  = $(this).find('.vl-total').text().trim();
                const compra = parseValor(compraTxt);
                const venda  = parseValor(vendaTxt);
                custoTotal += compra;
                subtotal   += venda;
            });
            subtotal += vl_p_s;
            $('#custoTotal_txt').text('R$ ' + custoTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
            $('#subtotal_txt').text('R$ ' + subtotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
            $('#id_subtotal').val(subtotal.toFixed(2));
            $('#id_vl_form_pgto').val(subtotal.toFixed(2));
            const descontoRaw = $('#id_desconto').length ? $('#id_desconto').val() : '0';
            const acrescimoRaw = $('#id_acrescimo').length ? $('#id_acrescimo').val() : '0';
            const desconto  = parseValor(descontoRaw);
            const acrescimo = parseValor(acrescimoRaw);
            const total = subtotal - desconto + acrescimo;
            $('#desconto').text('R$ ' + desconto.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
            $('#acrescimo').text('R$ ' + acrescimo.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
            $('#total_txt').text('R$ ' + total.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
            $('#id_total').val(total.toFixed(2));
            const margemLucro = subtotal > 0 ? ((subtotal - custoTotal) / subtotal) * 100 : 0;
            $('#margem_txt').text(margemLucro.toFixed(2) + '%');
            calcularValorForma();
            somaFormas();
            resolve();
        });
    }
    atualizarSubtotal();
    function parseValor(v) {
        if (v === null || v === undefined) return 0;
        v = String(v).trim();
        if (v === '') return 0;
        if (v.match(/,\d{1,2}$/)) {
            v = v.replace(/\./g, '').replace(',', '.');
            return parseFloat(v) || 0;
        }
        if (v.match(/\.\d{1,2}$/)) {
            v = v.replace(/,/g, '');
            return parseFloat(v) || 0;
        }
        v = v.replace(',', '.');
        return parseFloat(v) || 0;
    }
    function converterValor(v) {
        if (v === null || v === undefined) return 0;

        v = v.toString().trim();

        // Se tem vírgula → assume padrão BR
        if (v.includes(',')) {
            return Number(v.replace(/\./g, '').replace(',', '.')) || 0;
        }

        // Caso padrão americano
        return Number(v) || 0;
    }
    function calcularValorForma() {
        const totalValor = parseValor($('#id_total').val() || $('#total_txt').text());
        let totalPago = 0;
        $('#itensTableForm tbody tr').each(function() {
            const valor = parseValor($(this).find('td:nth-child(3)').text());
            totalPago += valor;
        });
        let restante = totalValor - totalPago;
        restante = Math.max(0, Math.round(restante * 100) / 100);
        $('#id_vl_form_pgto').val(restante.toFixed(2));
    }
    function verificarTotalFormas() {
        const totalValor = parseValor($('#id_total').val() || $('#total_txt').text());
        let totalFormas = 0;
        $('#itensTableForm tbody tr').each(function () {totalFormas += parseValor($(this).find('td:nth-child(3)').text());});
        const totalArred = parseFloat(totalValor.toFixed(2));
        const formasArred = parseFloat(totalFormas.toFixed(2));
        $("#somaFormas").text(formasArred.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        if (Math.abs(totalArred - formasArred) > 0.01) {
            $('#form_pgtoBtn').click();  // exibe modal de erro, se necessário
            return false;
        }
        return true;
    }
    function somaFormas() {
        let soma = 0;
        const linhas = $('#itensTableForm tbody tr').filter(function () {return $(this).find('td').length > 0;});
        if (linhas.length === 0) {
            $("#somaFormas").text("R$ 0,00");
            return true;
        }
        linhas.each(function () {
            const valor = parseValor($(this).find('td:nth-child(3)').text());
            soma += valor;
        });
        const total = parseFloat(soma.toFixed(2));
        $("#somaFormas").text("R$ " + total.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        return true;
    }
    $('#id_desconto, #id_acrescimo').on('input', function () {
        atualizarSubtotal();
        calcularValorForma();
        somaFormas();
    });
    function gerarPortas() {
        const qtd = parseInt($('#qtd_portas').val());
        if (isNaN(qtd) || qtd < 1) {
            toast(`${ic_amarelo} Informe uma quantidade válida de Portas!`, cor_amarelo);
            return;
        }
        if (window.prodManager?.data) prodManager.data = {};
        if (window.prodAdcManager?.data) prodAdcManager.data = {};
        resetarControleRegras();
        $("#tabelaPortasResumo tbody").empty();
        $("#accordionProdutos").empty();
        $("#accordionAdicionais").empty();
        for (let i = 1; i <= qtd; i++) {
            $("#tabelaPortasResumo tbody").append(`
                <tr id="linha_resumo_${i}" class="linha-porta" data-porta="${i}">
                    <td data-label="Porta:" class="num-porta mobile-3col">${i}</td>
                    <td data-label="Largura:" class="mobile-2col"><input type="text" class="form-control form-control-sm larg" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Altura:" class="mobile-2col"><input type="text" class="form-control form-control-sm alt" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Lg. Corte:" class="mobile-2col"><input readonly class="form-control form-control-sm larg-corte" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="At. Corte:" class="mobile-2col"><input readonly class="form-control form-control-sm alt-corte" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Qtd. Lâm.:" class="mobile-2col"><input readonly class="form-control form-control-sm qtd-laminas" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="M²:" class="mobile-2col"><input readonly class="form-control form-control-sm m2" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Ft. Peso:" class="mobile-2col"><input readonly class="form-control form-control-sm ft-peso" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Peso:" class="mobile-2col"><input readonly class="form-control form-control-sm peso" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Eix. Mot.:" class="mobile-2col"><input readonly class="form-control form-control-sm eix-mot" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Rolo:" class="mobile-full"><input readonly class="form-control form-control-sm rolo" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Tipo Lâmina:" class="mobile-full">
                        <select class="form-select form-select-sm tipo-lamina" data-porta="${i}">
                            <option value="Fechada">Fechada</option>
                            <option value="Transvision">Transvision</option>
                        </select>
                    </td>
                    <td data-label="Tipo Vão:" class="mobile-full">
                        <select class="form-select form-select-sm tipo-vao" data-porta="${i}">
                            <option value="Fora do Vão">Fora do Vão</option>
                            <option value="Dentro do Vão">Dentro do Vão</option>
                            <option value="1 Lado Dentro do Vão">1 Lado Dentro do Vão</option>
                        </select>
                    </td>
                    <td data-label="Guia Esquerdo:" class="mobile-full">
                        <select class="form-select form-select-sm guia-esq" data-porta="${i}">
                            <option value="Dentro do Vão">Dentro do Vão</option>
                            <option value="Fora do Vão">Fora do Vão</option>
                        </select>
                    </td>
                    <td data-label="Guia Direito:" class="mobile-full">
                        <select class="form-select form-select-sm guia-dir" data-porta="${i}">
                            <option value="Dentro do Vão">Dentro do Vão</option>
                            <option value="Fora do Vão">Fora do Vão</option>
                        </select>
                    </td>
                    <td data-label="Exc.:" class="text-center mobile-full">
                        <button type="button" class="btn btn-danger btn-sm removerPorta" data-porta="${i}"><i class="fa-solid fa-trash-can"></i></button>
                    </td>
                </tr>
            `);
            $(`.rolo[data-porta="${i}"]`).val("0.60");
            $("#accordionProdutos").append(criarAcordeonProdutos(i));
            $("#accordionAdicionais").append(criarAcordeonAdicionais(i));
            recalcularTotaisPorta(i);
        }
    }
    $(document).on('focus', '.id_larg, .larg-corte, .alt-corte, .qtd-laminas, .m2, .ft-peso, .qtd-prod-adc, .qtd-prod, .valor-prod, .valor-prod-adc', function () {
        if (!$(this).data('mask-applied')) {$(this).mask('00000.00', { reverse: true }).data('mask-applied', true);}
    });
    function inicializarCamposDecimais() {
        const CAMPOS = '.larg, .alt';
        $(CAMPOS).each(function () {
            if (!$(this).val()) {$(this).val('0.00');}
        });
    }
    const CAMPOS_DECIMAIS = '.larg, .alt';
    // evita duplicar evento
    $(document).off('focus.decimal').on('focus.decimal', CAMPOS_DECIMAIS, function () {
        let val = $(this).val();
        if (!val || val === '0.00') {$(this).data('raw', '');}
        else {$(this).data('raw', val.replace('.', ''));}
        this.select();
    });
    $(document).off('input.decimal').on('input.decimal', CAMPOS_DECIMAIS, function () {
        let valor = $(this).val();
        let raw = valor.replace(/\D/g, '');
        $(this).data('raw', raw);
        if (!raw) {
            $(this).val('0.00');
            if ($(this).hasClass('alt')) {
                atualizarAltCorte($(this));
            }
            return;
        }
        let num = (parseInt(raw, 10) / 100).toFixed(2);
        $(this).val(num);
        if ($(this).hasClass('alt')) {
            atualizarAltCorte($(this));
        }
    });
    $(document).off('blur.decimal').on('blur.decimal', CAMPOS_DECIMAIS, function () {
        let val = $(this).val();
        if (!val || val === '') {$(this).val('0.00');}
        if ($(this).hasClass('alt')) {atualizarAltCorte($(this));}
    });
    $(document).on('change', '.guia-esq, .guia-dir', function() {console.log("ALTEROU GUIA:", $(this).val(), "PORTA:", $(this).data('porta'));});
    function criarFormularioProduto(num) {
        return `
            <div class="row g-2 mb-3 form-produto" data-porta="${num}">
                <div class="col-md-2">
                    <label class="form-label">Cód. Produto</label>
                    <div class="input-group">
                        <input type="text" class="form-control form-control-sm cod-prod" data-porta="${num}" name="cod-prod" placeholder="Cód. Produto">
                        <button class="btn btn-outline-dark btn-sm btn-busca-prod" type="button" data-porta="${num}" data-bs-toggle="modal" data-bs-target="#produtoModal"><i class="fa-solid fa-magnifying-glass"></i></button>
                    </div>
                </div>
                <div class="col-md-3">
                    <label class="form-label">Descrição</label>
                    <input type="text" class="form-control form-control-sm desc-prod" data-porta="${num}" name="desc-prod" disabled>
                </div>
                <div class="col-md-1">
                    <label class="form-label">Unidade</label>
                    <input type="text" class="form-control form-control-sm unid-prod" data-porta="${num}" name="unid-prod" disabled>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Valor</label>
                    <input type="text" class="form-control form-control-sm valor-prod text-end" name="valor-prod" value="0.00" style='color: darkgreen; font-weight: bold; background: honeydew;' data-porta="${num}">
                </div>
                <div class="col-md-2">
                    <label class="form-label">Qtde.</label>
                    <input type="text" class="form-control form-control-sm qtd-prod" name="qtd-prod" placeholder="0.00" value="0.00" data-porta="${num}">
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button type="button" class="btn btn-success btn-sm btn-add-prod" data-porta="${num}"><i class="fas fa-plus"></i> Incluir</button>
                </div>
            </div>
        `;
    }
    function criarAcordeonProdutos(num) {
        return `
            <div class="accordion-item acc-produto porta-${num}" id="accProd_${num}" data-porta="${num}">
                <h2 class="accordion-header" id="headingProd_${num}">
                    <button class="accordion-button collapsed fw-bold" type="button" data-bs-toggle="collapse" data-bs-target="#collapseProd_${num}" style="max-height: 30px; background-color: #A9A9A9;">
                        Produtos – Porta ${num}
                    </button>
                </h2>
                <div id="collapseProd_${num}" class="accordion-collapse collapse">
                    <div class="accordion-body table-container w-100">
                        ${criarFormularioProduto(num)}
                        <table class="table table-bordered table-sm table-striped tabela-produtos" id="tblProd_${num}">
                            <thead class="table-dark">
                                <tr>
                                    <th>Código</th>
                                    <th>Descrição</th>
                                    <th>Unidade</th>
                                    <th>Vl. Compra</th>
                                    <th>Vl. Un.</th>
                                    <th>Qtde.</th>
                                    <th>Tot. Compra</th>
                                    <th>Vl. Tot.</th>
                                    <th style="width: 80px;">Ações</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                        <div class="d-flex justify-content-end gap-4 mt-2 porta-totais" data-porta="${num}">
                            <span>
                                <strong>Total Compra:</strong>
                                <span style="padding-left: 10px; padding-right: 10px;" class="border border-danger-subtle rounded-4 bg-danger-subtle fw-bold" id="totCompra_porta_${num}">0</span>
                            </span>
                            <span>
                                <strong>Total Venda:</strong>
                                <span style="padding-left: 10px; padding-right: 10px;" class="border border-success-subtle rounded-4 bg-success-subtle fw-bold" id="totVenda_porta_${num}">0</span>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    function criarFormularioAdicional(num) {
        return `
            <div class="row g-2 mb-3 form-adicional" data-porta="${num}">
                <div class="col-md-2">
                    <label class="form-label">Cód. Produto</label>
                    <div class="input-group">
                        <input type="text" class="form-control form-control-sm cod-prod-adc" name="cod-prod-adc" data-porta="${num}" placeholder="Cód. Produto">
                        <button class="btn btn-outline-dark btn-sm btn-busca-prod-adc" type="button" data-porta="${num}" data-bs-toggle="modal" data-bs-target="#produtoAdcModal"><i class="fa-solid fa-magnifying-glass"></i></button>
                    </div>
                </div>
                <div class="col-md-2">
                    <label class="form-label">Descrição</label>
                    <input type="text" class="form-control form-control-sm desc-prod-adc" name="desc-prod-adc" data-porta="${num}" disabled>
                </div>
                <div class="col-md-1">
                    <label class="form-label">Unidade</label>
                    <input type="text" class="form-control form-control-sm unid-prod-adc" name="unid-prod-adc" data-porta="${num}" disabled>
                </div>
                <input type="hidden" class="vl-compra-prod-adc" data-porta="${num}" value="0.00">
                <div class="col-md-2">
                    <label class="form-label">Valor</label>
                    <input type="text" class="form-control form-control-sm valor-prod-adc text-end" name="valor-prod-adc" value="0.00" style='color: darkgreen; font-weight: bold; background: honeydew;' data-porta="${num}">
                </div>
                <div class="col-md-1">
                    <label class="form-label">Qtde.</label>
                    <input type="text" class="form-control form-control-sm qtd-prod-adc" placeholder="0.00" value="0.00" name="qtd-prod-adc" data-porta="${num}">
                </div>
                <div class="col-md-2 mt-2 campo-lado-adc d-none">
                    <label class="form-label">Lado</label>
                    <select class="form-select form-select-sm lado-adc" data-porta="${num}">
                        <option value="E" selected>Esquerdo</option>
                        <option value="D">Direito</option>
                        <option value="C">Centro</option>
                    </select>
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button type="button" class="btn btn-success btn-sm btn-add-prod-adc" data-porta="${num}"><i class="fas fa-plus"></i> Incluir</button>
                </div>
            </div>
        `;
    }
    function criarAcordeonAdicionais(num) {
        return `
            <div class="accordion-item acc-adicional porta-${num}" id="accAdc_${num}" data-porta="${num}">
                <h2 class="accordion-header" id="headingAdc_${num}">
                    <button class="accordion-button collapsed fw-bold" type="button" data-bs-toggle="collapse" data-bs-target="#collapseAdc_${num}" style="max-height: 30px; background-color: #A9A9A9;">
                        Adicionais – Porta ${num}
                    </button>
                </h2>
                <div id="collapseAdc_${num}" class="accordion-collapse collapse">
                    <div class="accordion-body table-container w-100">
                        ${criarFormularioAdicional(num)}
                        <table class="table table-bordered table-sm table-striped tabela-adicionais" id="tblAdc_${num}">
                            <thead class="table-dark">
                                <tr>
                                    <th>Código</th>
                                    <th>Descrição</th>
                                    <th>Unidade</th>
                                    <th>Vl. Compra</th>
                                    <th>Vl. Un.</th>
                                    <th>Qtde.</th>
                                    <th>Tot. Compra</th>
                                    <th>Vl. Tot.</th>
                                    <th style="width: 80px;">Ações</th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                        <div class="d-flex justify-content-end gap-4 mt-2 porta-totais" data-porta="${num}">
                            <span>
                                <strong>Total Compra:</strong>
                                <span style="padding-left: 10px; padding-right: 10px;" class="border border-danger-subtle rounded-4 bg-danger-subtle fw-bold" id="totCompraAdc_porta_${num}">0</span>
                            </span>
                            <span>
                                <strong>Total Venda:</strong>
                                <span style="padding-left: 10px; padding-right: 10px;" class="border border-success-subtle rounded-4 bg-success-subtle fw-bold" id="totVendaAdc_porta_${num}">0</span>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    function adicionarItemTabela({manager, tabelaId, porta, dados, extra = {}}) {
        const p = Number(porta);
        manager.data[p] ??= [];
        let item = manager.data[p].find(x => Number(x.cod) === Number(dados.cod));
        if (!item) {
            item = {id: Number(dados.cod), cod: Number(dados.cod), desc: dados.desc || '', unid: dados.unid || '', vl_compra: parseFloat(dados.vl_compra) || 0, vl_unit: parseFloat(dados.vl) || 0,
                qtd_calc: 0, qtd_final: 0, qtd_manual: true, ativo: true, ...extra
            };
            manager.data[p].push(item);
        }
        item.desc = dados.desc || item.desc;
        item.unid = dados.unid || item.unid;
        item.qtd_final = parseFloat(dados.qtd) || 0;
        item.qtd_manual = true;
        item.ativo = item.qtd_final > 0;
        item.vl_unit = parseFloat(dados.vl) || 0;
        item.vl_compra = parseFloat(dados.vl_compra) || item.vl_compra || 0;
        Object.assign(item, extra);
        const totCompra = item.qtd_final * item.vl_compra;
        const vlTotal = item.qtd_final * item.vl_unit;
        item.tot_compra = totCompra;
        item.vl_total = vlTotal;
        let $row = $(`#${tabelaId}_${p} tbody tr[data-item-id="${item.cod}"]`);
        if (!$row.length) {
            $row = $(montarTrProduto({porta: p, item, modalEditar: tabelaId === 'tblAdc' ? 'editItemAdcModal' : 'editItemModal'}));
            $(`#${tabelaId}_${p} tbody`).append($row);
        }
        atualizarLinha($row, item);
        atualizarTabelaPorta(p);
        atualizarSubtotal();
        atualizarJSONPortas();
    }
    function atualizarLinha($row, item) {
        const f = v => Number(v || 0).toFixed(2);
        $row.find('.td-desc').text(item.desc);
        $row.find('.td-unid').text(item.unid);
        $row.find('.td-vl-compra').text(f(item.vl_compra));
        $row.find('.vl-unit').text(f(item.vl_unit));
        $row.find('.qtd-produto').text(f(item.qtd_final));
        $row.find('.tot-compra').text(f(item.tot_compra));
        $row.find('.vl-total').text(f(item.vl_total));
    }
    function adicionarProdutoNaTabela(porta, dados) {
        adicionarItemTabela({manager: prodManager, tabelaId: 'tblProd', porta, dados});
    }
    function adicionarAdicionalNaTabela(porta, dados) {
        adicionarItemTabela({manager: prodAdcManager, tabelaId: 'tblAdc', porta, dados, extra: {lado: dados.lado || '', especifico: dados.especifico || ''}});
    }
    $(document).on("click", ".btn-add-prod", function () {
        const porta = $(this).data("porta");
        const cod  = $(`.cod-prod[data-porta="${porta}"]`).val();
        const desc = $(`.desc-prod[data-porta="${porta}"]`).val();
        const unid = $(`.unid-prod[data-porta="${porta}"]`).val();
        const qtd  = parseFloat($(`.qtd-prod[data-porta="${porta}"]`).val().replace(',', '.')) || 0;
        const vl   = parseFloat($(`.valor-prod[data-porta="${porta}"]`).val().replace(',', '.')) || 0;
        if (!cod || !desc || qtd <= 0) {
            alert('Produto principal incompleto');
            return;
        }
        adicionarProdutoNaTabela(porta, { cod, desc, unid, qtd, vl });
        $(`.cod-prod[data-porta="${porta}"], .desc-prod[data-porta="${porta}"], .unid-prod[data-porta="${porta}"], .valor-prod[data-porta="${porta}"], .qtd-prod[data-porta="${porta}"]`).val('');
        $(`.cod-prod[data-porta="${porta}"]`).focus();
    });
    $(document).on("click", ".btn-add-prod-adc", function () {
        const porta = $(this).data("porta");
        const $form = getFormAdcByPorta(porta);
        const cod  = $(`.cod-prod-adc[data-porta="${porta}"]`).val();
        const desc = $(`.desc-prod-adc[data-porta="${porta}"]`).val();
        const unid = $(`.unid-prod-adc[data-porta="${porta}"]`).val();
        const qtd  = parseFloat($(`.qtd-prod-adc[data-porta="${porta}"]`).val().replace(',', '.')) || 0;
        const vl   = parseFloat($(`.valor-prod-adc[data-porta="${porta}"]`).val().replace(',', '.')) || 0;
        const vl_compra_raw = $form.find('.vl-compra-prod-adc').val();
        const vl_compra = parseFloat(String(vl_compra_raw || '0').replace(',', '.')) || 0;
        const lado = $(`.lado-adc[data-porta="${porta}"]`).val() || '';
        const especifico = ($form.data('especifico') || '').trim();
        console.log('ADD ADC', { cod, desc, unid, qtd, vl, vl_compra, vl_compra_raw });
        const precisaLado = ['Portinhola', 'Alçapão', 'Coluna Removível'].includes(especifico);
        if (!cod || !desc || qtd <= 0) {
            alert('Produto adicional incompleto');
            return;
        }
        if (precisaLado && !lado) {
            alert('Selecione o lado do adicional');
            $(`.lado-adc[data-porta="${porta}"]`).focus();
            return;
        }
        adicionarAdicionalNaTabela(porta, {cod, desc, unid, qtd, vl, vl_compra, lado, especifico});
        $(`.cod-prod-adc[data-porta="${porta}"], .desc-prod-adc[data-porta="${porta}"], .unid-prod-adc[data-porta="${porta}"], .valor-prod-adc[data-porta="${porta}"], .qtd-prod-adc[data-porta="${porta}"]`).val('');
        $form.find('.vl-compra-prod-adc').val('0.00');
        $(`.lado-adc[data-porta="${porta}"]`).val('');
        $form.removeData('especifico');
        $form.find('.campo-lado-adc').addClass('d-none');
        $(`.cod-prod-adc[data-porta="${porta}"]`).focus();
    });
    function formatarBR(valor) {return new Intl.NumberFormat('pt-BR', {style: 'currency', currency: 'BRL'}).format(valor);}
    function observarTotaisPorta(porta) {
        const tabela = document.querySelector("#tblProd_" + porta + " tbody");
        if (!tabela) return;
        const observer = new MutationObserver(() => {recalcularTotaisPorta(porta);});
        observer.observe(tabela, {childList: true, subtree: true, characterData: true});
        const tabelaAdc = document.querySelector("#tblAdc_" + porta + " tbody");
        if (tabelaAdc) {
            const observerAdc = new MutationObserver(() => {recalcularTotaisPorta(porta);});
            observerAdc.observe(tabelaAdc, {childList: true, subtree: true, characterData: true});
        }
    }
    $('[id^="tblProd_"]').each(function () {
        const porta = this.id.split('_')[1];
        observarTotaisPorta(porta);
    });
    function recalcularTotaisPorta(porta) {
        let totalCompra = 0;
        let totalVenda = 0;
        let totalCompraAdc = 0;
        let totalVendaAdc = 0;
        $("#tblProd_" + porta + " tbody tr").each(function () {
            const compra = parseValor($(this).find(".tot-compra").text());
            const venda  = parseValor($(this).find(".vl-total").text());
            totalCompra += compra;
            totalVenda += venda;
        });
        $("#tblAdc_" + porta + " tbody tr").each(function () {
            const compra = parseValor($(this).find(".tot-compra").text());
            const venda  = parseValor($(this).find(".vl-total").text());
            totalCompraAdc += compra;
            totalVendaAdc += venda;
        });
        $("#totCompra_porta_" + porta).text(formatarBR(totalCompra));
        $("#totVenda_porta_" + porta).text(formatarBR(totalVenda));
        $("#totCompraAdc_porta_" + porta).text(formatarBR(totalCompraAdc));
        $("#totVendaAdc_porta_" + porta).text(formatarBR(totalVendaAdc));
    }
    $(".porta-totais").each(function () {
        const porta = $(this).data("porta");
        recalcularTotaisPorta(porta);
    });
    $(document).on("blur", ".alt", async function () {
        const idTabela = $('#id_tabela_preco').val();
        if (!idTabela) {
            alert("Selecione primeiro a TABELA DE PREÇO.");
            $(this).val('');
            return;
        }
        const porta = $(this).data("porta");
        const lg = parseFloat($(`.larg[data-porta="${porta}"]`).val()) || 0;
        const at = parseFloat($(`.alt[data-porta="${porta}"]`).val()) || 0;
        if (lg <= 0 || at <= 0) return;
        medidasCtrl[porta] ??= {};
        const ctrl = medidasCtrl[porta];
        const primeiraVez = !ctrl.larg && !ctrl.alt;
        const mudouMedida = ctrl.larg !== lg || ctrl.alt !== at;
        if (!mudouMedida) {
            atualizarSubtotal();
            return;
        }
        ctrl.larg = lg;
        ctrl.alt  = at;
        iniciarLoading();
        calcLgCorte(porta);  // PRIMEIRO
        calcM2(porta);
        calcFtPeso(porta);
        calcPeso(porta);
        calcularEixoMotor(porta);
        calcQtdLam(porta);
        await carregarProdutosIniciais(porta);
        atualizarSubtotal();
        calcularValorForma();
        somaFormas();
        finalizarLoading();
    });
    $(document).on("click", ".removerPorta", function () {
        const porta = $(this).data("porta");
        resetarPorta(porta);
        $("#linha_resumo_" + porta).remove();
        $("#accProd_" + porta).remove();
        $("#accAdc_" + porta).remove();
        reindexarPortas();
        atualizarSubtotal();
    });
    $(document).on('click', '.deleteBtn', function () {
        const $tr   = $(this).closest('tr');
        const porta = Number($tr.data('porta'));
        const id    = Number($tr.data('item-id'));
        [prodManager, prodAdcManager].forEach(mgr => {
            const item = (mgr.data[porta] || []).find(x => Number(x.cod) === id);
            if (item) { item.ativo = false; item.qtd_final = 0; }
        });
        $tr.remove();
        recalcularTotaisPorta(porta);
        atualizarSubtotal();
        atualizarJSONPortas();
    });
    function resetarPorta(porta) {
        if (window.prodManager?.data) {prodManager.data[porta] = [];}
        if (window.prodAdcManager?.data) {prodAdcManager.data[porta] = [];}
        $(`#tblProd_${porta} tbody`).empty();
        $(`#tblAdc_${porta} tbody`).empty();
    }
    function reindexarPortas() {
        let novoIndice = 1;
        $("#tabelaPortasResumo tbody tr").each(function () {
            $(this).attr("id", "linha_resumo_" + novoIndice);
            $(this).find(".num-porta").text(novoIndice);
            $(this).find("input, select").each(function () {$(this).attr("data-porta", novoIndice);});
            $(this).find(".removerPorta").attr("data-porta", novoIndice);
            novoIndice++;
        });
        novoIndice = 1;
        $("#accordionProdutos .acc-produto").each(function () {
            $(this).attr("id", "accProd_" + novoIndice);
            $(this).attr("data-porta", novoIndice);
            $(this).find(".accordion-header").attr("id", "headingProd_" + novoIndice);
            $(this).find(".accordion-button").attr("data-bs-target", "#collapseProd_" + novoIndice).text("Produtos – Porta " + novoIndice);
            $(this).find(".accordion-collapse").attr("id", "collapseProd_" + novoIndice);
            $(this).find(".tabela-produtos").attr("id", "tblProd_" + novoIndice);
            novoIndice++;
        });
        novoIndice = 1;
        $("#accordionAdicionais .acc-adicional").each(function () {
            $(this).attr("id", "accAdc_" + novoIndice);
            $(this).attr("data-porta", novoIndice);
            $(this).find(".accordion-header").attr("id", "headingAdc_" + novoIndice);
            $(this).find(".accordion-button").attr("data-bs-target", "#collapseAdc_" + novoIndice).text("Adicionais – Porta " + novoIndice);
            $(this).find(".accordion-collapse").attr("id", "collapseAdc_" + novoIndice);
            $(this).find(".tabela-adicionais").attr("id", "tblAdc_" + novoIndice);
            novoIndice++;
        });
        $("#qtd_portas").val($("#tabelaPortasResumo tbody tr").length);
        if (typeof atualizarJSONPortas === "function") {atualizarJSONPortas();}
    }
    function getCSRFToken() {
        return document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
    }
        // 1️⃣ NOVA FUNÇÃO: Carregar produtos pela primeira vez (baseado em regras)
    async function carregarProdutosIniciais(porta) {
        const contexto = {
            largura: getFloat(`.larg[data-porta="${porta}"]`), altura: getFloat(`.alt[data-porta="${porta}"]`), larg_c: getFloat(`.larg-corte[data-porta="${porta}"]`),
            alt_c: getFloat(`.alt-corte[data-porta="${porta}"]`), m2: getFloat(`.m2[data-porta="${porta}"]`), peso: getFloat(`.peso[data-porta="${porta}"]`),
            qtd_lam: getFloat(`.qtd-laminas[data-porta="${porta}"]`), ft_peso: getFloat(`.ft-peso[data-porta="${porta}"]`), eix_mot: getFloat(`.eix-mot[data-porta="${porta}"]`),
            rolo: getFloat(`.rolo[data-porta="${porta}"]`), tipo_lamina: $(`.tipo-lamina[data-porta="${porta}"]`).val(), tipo_pintura: $('#id_tp_pintura').val(),
            tem_pintura: $('#id_pintura').val() === 'Sim'
        };
        const baseUrl = window.location.origin;

        const resp = await fetch(`${baseUrl}/regras_produto/aplicar_regras_porta/`, {
            method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()}, body: JSON.stringify({tabela_id: getTabelaPreco(), contexto: contexto})
        });
        if (!resp.ok) {
            const text = await resp.text();
            console.error("Erro HTTP:", resp.status, text);
            return;
        }

        const data = await resp.json();
        if (!data.success) {
            console.error('Erro ao aplicar regras:', data.error);
            return;
        }
        // Remove apenas produtos de regras antigas (mantém produtos manuais)
        prodManager.data[porta] = (prodManager.data[porta] || []).filter(
            item => !item.regra_origem || item.qtd_manual
        );
        prodAdcManager.data[porta] = (prodAdcManager.data[porta] || []).filter(
            item => !item.regra_origem || item.qtd_manual
        );
        // Remove linhas antigas de regras no DOM (mantém manuais)
        $(`#tblProd_${porta} tbody tr[data-regra-origem]`).not('[data-manual="true"]').remove();
        $(`#tblAdc_${porta} tbody tr[data-regra-origem]`).not('[data-manual="true"]').remove();
        // Adiciona novos produtos vindos do backend
        data.produtos.forEach(item => {
            // ✅ Determina tabela baseado no tp_prod retornado do backend
            const ehAdicional = item.tp_prod === 'Adicional';
            const manager = ehAdicional ? prodAdcManager : prodManager;
            const tabelaId = ehAdicional ? 'tblAdc' : 'tblProd';
            const modalId = ehAdicional ? 'editItemAdcModal' : 'editItemModal';
            // Cria objeto do produto
            const novoProduto = {id: item.id, cod: item.codigo, desc: item.desc_prod, unid: item.unidProd, vl_compra: item.vl_compra, vl_unit: item.vl_unit,
                qtd_final: item.qtd, qtd_manual: false, regra_origem: item.regra_origem || null, tp_prod: item.tp_prod, ativo: true};
            // Adiciona ao manager correto
            manager.data[porta].push(novoProduto);
            // Adiciona linha na tabela correta
            $(`#${tabelaId}_${porta} tbody`).append(montarTrProduto({porta, item: novoProduto, modalEditar: modalId, regraOrigem: item.regra_origem || ''}));
        });
        recalcularTotaisPorta(porta);
    }
    // 2️⃣ FUNÇÃO ATUAL: Recalcular qtd de produtos JÁ EXISTENTES
    async function atualizarTabelaPorta(porta) {
        const ctrl = medidasCtrl[porta] || {};
        const larg   = Number(ctrl.larg)   || 0;
        const alt    = Number(ctrl.alt)    || 0;
        const larg_c = parseFloat($(`.larg-corte[data-porta="${porta}"]`).val()) || 0;
        const alt_c  = parseFloat($(`.alt-corte[data-porta="${porta}"]`).val()) || 0;
        const m2     = parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;
        const eix_mot = parseFloat($(`.eix-mot[data-porta="${porta}"]`).val()) || 0;
        const qtd_lam = parseFloat($(`.qtd-laminas[data-porta="${porta}"]`).val()) || 0;
        const ft_peso = parseFloat($(`.ft-peso[data-porta="${porta}"]`).val()) || 0;
        const peso   = parseFloat($(`.peso[data-porta="${porta}"]`).val()) || 0;
        const rolo   = parseFloat($(`.rolo[data-porta="${porta}"]`).val()) || 0;
        const contexto = { alt, alt_c, larg, larg_c, m2, peso, qtd_lam, rolo, ft_peso, eix_mot };
        const produtos = [];
        const idsAdicionados = new Set();
        const linhasProd = $(`#tblProd_${porta} tbody tr`).length;
        const linhasAdc  = $(`#tblAdc_${porta} tbody tr`).length;
        if (linhasProd === 0 && linhasAdc === 0) {
            console.warn("Tabela ainda não carregada, abortando cálculo...");
            return;
        }
        function adicionarProduto($tr) {
            const id = Number($tr.data('item-id'));
            if (!id) return;
            if (idsAdicionados.has(id)) return;

            idsAdicionados.add(id);

            const qtdManual = $tr.data('qtd-manual');
            let qtd;

            if (qtdManual !== undefined && qtdManual !== null) {
                qtd = Number(qtdManual);
            } else {
                const txt = $tr.find('.qtd-produto').text().trim();
                const qtdExibida = parseFloat(txt.replace(',', '.')) || 0;
                qtd = qtdExibida ? Number(qtdExibida) : 0;
            }

            produtos.push({
                id: id,
                qtd: qtd
            });
        }
        $(`#tblProd_${porta} tbody tr`).each(function () {
            adicionarProduto($(this));
        });

        $(`#tblAdc_${porta} tbody tr`).each(function () {
            adicionarProduto($(this));
        });
        if (produtos.length === 0) return;
        const resp = await fetch('/regras_produto/calcular_orcamento/', {
            method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
            body: JSON.stringify({tabela_id: getTabelaPreco(), contexto: contexto, produtos: produtos})
        });
        const data = await resp.json();
        console.log('Resultado backend:', data);
        aplicarResultadoCalculo(porta, data);
        recalcularTotaisPorta(porta);
    }
    function atualizarQtdNoManager(porta, id, qtd) {
        const itemProd = (prodManager.data[porta] || []).find(i => i.id === id);
        if (itemProd) { itemProd.qtd_final = qtd; return; }
        const itemAdc = (prodAdcManager.data[porta] || []).find(i => i.id === id);
        if (itemAdc) { itemAdc.qtd_final = qtd; }
    }
    function aplicarResultadoCalculo(porta, data) {
        let totalCompraProd = 0;
        let totalVendaProd  = 0;
        let totalCompraAdc  = 0;
        let totalVendaAdc   = 0;
        const idsRetornados = new Set(data.itens.map(i => Number(i.id)));
        $(`#tblProd_${porta} tbody tr`).each(function () {
            const $tr = $(this);
            const id = Number($tr.data('item-id'));
            const origem = $tr.data('regra-origem');
            if (!origem) return;
            const qtdManual = $tr.data('qtd-manual');
            let qtdExibida = null;
            if (qtdManual !== undefined && qtdManual !== null) {
                qtdExibida = Number(qtdManual) || 0;
            } else {
                const txt = $tr.find('.qtd-produto').text().replace(/\./g, '').replace(',', '.').trim();
                qtdExibida = txt ? Number(txt) : 0;
            }
            if (qtdExibida > 0) {
                return;
            }
            if (!idsRetornados.has(id)) {
                $tr.hide();
            }
        });
        $(`#tblAdc_${porta} tbody tr`).each(function () {
            const $tr = $(this);
            const id = Number($tr.data('item-id'));
            const origem = $tr.data('regra-origem');
            if (!origem) return;
            const qtdManual = $tr.data('qtd-manual');
            let qtdExibida = null;
            if (qtdManual !== undefined && qtdManual !== null) {
                qtdExibida = Number(qtdManual) || 0;
            } else {
                const txt = $tr.find('.qtd-produto').text().replace(/\./g, '').replace(',', '.').trim();
                qtdExibida = txt ? Number(txt) : 0;
            }
            if (qtdExibida > 0) {
                return;
            }
            if (!idsRetornados.has(id)) {
                $tr.hide();
            }
        });
        data.itens.forEach(item => {
            let $tr = $(`#tblProd_${porta} tbody tr[data-item-id="${item.id}"]`);
            let tipo = 'prod';
            if (!$tr.length) {
                $tr = $(`#tblAdc_${porta} tbody tr[data-item-id="${item.id}"]`);
                tipo = 'adc';
            }
            if (!$tr.length) return;
            let qtdManual = $tr.data('qtd-manual');
            let qtdBackend = Number(item.qtd) || 0;
            let qtd;
            if (qtdManual !== undefined && qtdManual !== null && qtdManual > 0) {
                qtd = Number(qtdManual);
            } else {
                qtd = qtdBackend;
            }
            if ($tr.data('regra-origem') && qtd <= 0) {
                $tr.hide();
                return;
            }
            $tr.show();
            const vlCompra = parseValor($tr.find('.td-vl-compra').text());
            const vlUnit   = parseValor($tr.find('.vl-unit').text());
            const totCompra = isFinite(vlCompra * qtd) ? vlCompra * qtd : 0;
            const totVenda  = isFinite(vlUnit * qtd) ? vlUnit * qtd : 0;
            $tr.find('.qtd-produto').text(qtd.toFixed(2));
            $tr.find('.tot-compra').text(totCompra.toFixed(2));
            $tr.find('.vl-total').text(totVenda.toFixed(2));
            atualizarQtdNoManager(porta, item.id, qtd);
            if (tipo === 'prod') {
                totalCompraProd += totCompra;
                totalVendaProd  += totVenda;
            } else {
                totalCompraAdc += totCompra;
                totalVendaAdc  += totVenda;
            }
        });
        $(`#totCompra_porta_${porta}`).text("R$ " + totalCompraProd.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $(`#totVenda_porta_${porta}`).text("R$ " + totalVendaProd.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $(`#totCompraAdc_porta_${porta}`).text("R$ " + totalCompraAdc.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $(`#totVendaAdc_porta_${porta}`).text("R$ " + totalVendaAdc.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
    }
    medidasCtrl = [];
    $(".linha-porta").each(function () {
        atualizarJSONPortas();
    });
    function obterRegraProduto(codProd) {
        if (!REGRAS) {
            console.warn('REGRAS ainda não carregadas');
            return null;
        }
        return REGRAS[codProd] || null;
    }
    function hidratarManagers(portas) {
        prodManager.data    = {};
        prodAdcManager.data = {};
        medidasCtrl         = {};
        portas.forEach(porta => {
            const p = porta.numero;
            if (!p) return;
            medidasCtrl[p] = {
                larg: porta.largura, alt: porta.altura, m2: porta.m2, larg_c: porta.larg_corte, alt_c: porta.alt_corte, peso: porta.peso, ft_peso: porta.ft_peso, eix_mot: porta.eix_mot
            };
            prodManager.data[p] = (porta.produtos || []).map(item => ({
                id: Number(item.codProd), cod: Number(item.codProd), regra: obterRegraProduto(item.codProd), regra_origem: item.regra_origem || null, qtd_calc: Number(item.qtdProd), qtd_final: Number(item.qtdProd),
                vl_unit: Number(item.vl_unit || 0), vl_compra: Number(item.vl_compra || 0), qtd_manual: true, ativo: Number(item.qtdProd) > 0
            }));
            prodAdcManager.data[p] = (porta.adicionais || []).map(item => ({id: Number(item.codProd), cod: Number(item.codProd), regra: null, regra_origem: item.regra_origem || null,
                qtd_calc: Number(item.qtdProd), qtd_final: Number(item.qtdProd), vl_unit: Number(item.vl_unit  || 0), vl_compra: Number(item.vl_compra || 0), qtd_manual: false,
                ativo: Number(item.qtdProd) > 0}));
        });
    }
    function atualizarJSONPortas() {
        const portas = [];
        $('table[id^="tblProd_"]').each(function () {
            const p = this.id.split('_')[1];
            const produtos = (prodManager.data[p] || []).filter(i => i.ativo && i.qtd_final > 0).map(i => ({
                codProd: i.cod, qtdProd: i.qtd_final, vl_unit: i.vl_unit, vl_total: i.qtd_final * i.vl_unit, ativo: true, regra_origem: i.regra_origem || ''}));
            const adicionais = (prodAdcManager.data[p] || []).filter(i => i.ativo && i.qtd_final > 0).map(i => ({
                codProd: i.cod, qtdProd: i.qtd_final, vl_unit: i.vl_unit, vl_total: i.qtd_final * i.vl_unit, ativo: true, lado: i.lado || '', regra_origem: i.regra_origem || ''}));
            portas.push({
                numero: Number(p), produtos, adicionais, largura: getFloat(`.larg[data-porta="${p}"]`), altura: getFloat(`.alt[data-porta="${p}"]`), qtd_lam: getFloat(`.qtd-laminas[data-porta="${p}"]`),
                m2: getFloat(`.m2[data-porta="${p}"]`), larg_corte: getFloat(`.larg-corte[data-porta="${p}"]`), alt_corte: getFloat(`.alt-corte[data-porta="${p}"]`), rolo: getFloat(`.rolo[data-porta="${p}"]`),
                peso: getFloat(`.peso[data-porta="${p}"]`), ft_peso: getFloat(`.ft-peso[data-porta="${p}"]`), eix_mot: getFloat(`.eix-mot[data-porta="${p}"]`), tipo_lamina: $(`.tipo-lamina[data-porta="${p}"]`).val() || '',
                tipo_vao: $(`.tipo-vao[data-porta="${p}"]`).val() || '', op_guia_e: $(`.guia-esq[data-porta="${p}"]`).val() || '', op_guia_d: $(`.guia-dir[data-porta="${p}"]`).val() || ''});
        });
        $('#id_json_portas').val(JSON.stringify(portas));
        return true;
    }
    $(document).on('change', '.guia-esq, .guia-dir', function () {atualizarJSONPortas();});
    function getFloat(selector) {
        const el = $(selector);
        if (!el.length) return 0;
        const val = el.val();
        if (!val) return 0;
        return parseFloat(val.replace(',', '.')) || 0;
    }
    function getSelect2IdIfExists(selector) {
        const $el = $(selector);
        if ($el.length === 0) {return undefined;}
        const data = $el.select2('data') || [];
        return data.length ? data[0].id : null;
    }
    $('#openModalBtn').on('click', async function (e) {
        e.preventDefault();
        e.stopPropagation();
        await atualizarSubtotal();
        //Para Orçamentos
        const temPintura = $("#id_pintura").val();
        const corSelecionada = $("#id_cor").val();
        const filial = getSelect2IdIfExists('#id_vinc_fil');
        const solicitante = getSelect2IdIfExists('#id_solicitante');
        const cliente = getSelect2IdIfExists('#id_cli');
        //Para Entrada de Pedidos/NF
        const fornecedor = getSelect2IdIfExists('#id_fornecedor');
        const tipoPedido = $("#id_tipo").val();
        const numeracao = $("#id_numeracao").val();
        let campoInvalido = null;
        let nomeCampo = '';
        $('#createForm').find('[required]').each(function() {
            let valor = $(this).val();
            if (!valor || valor.trim() === '') {
                campoInvalido = $(this);
                let id = $(this).attr('id');
                nomeCampo = $('label[for="' + id + '"]').text().replace('*', '').trim();
                return false; // para no primeiro erro
            }
        });
        if (campoInvalido) {
            campoInvalido.addClass('is-invalid');
            campoInvalido.focus();
            toast(`${ic_amarelo} ${nomeCampo} deve ser preenchido!`, cor_amarelo);
            return false; // 🚨 ESSENCIAL
        }
        if (temPintura === "Sim" && (!corSelecionada || corSelecionada === "")) {
            toast(`${ic_amarelo} Escolha uma cor da pintura antes de gravar!`, cor_amarelo);
            $("#medidasBtn").click();
            return false;
        }
        if (filial !== undefined && !filial) {
            toast(`${ic_amarelo} Filial deve ser informada!`, cor_amarelo);
            $("#clienteBtn").click();
            return false;
        }
        if (fornecedor !== undefined && !fornecedor) {
            toast(`${ic_amarelo} Fornecedor deve ser informado!`, cor_amarelo);
            return false;
        }
        if ((!numeracao || numeracao === "") && tipoPedido === "Pedido") {
            toast(`${ic_amarelo} Numeração do Pedido deve ser informada!`, cor_amarelo);
            return false;
        } else if ((!numeracao || numeracao === "") && tipoPedido === "Nota Fiscal") {
            toast(`${ic_amarelo} Numeração da Nota Fiscal deve ser informada!`, cor_amarelo);
            return false;
        }
        if (solicitante !== undefined && !solicitante) {
            toast(`${ic_amarelo} Solicitante deve ser informado!`, cor_amarelo);
            $("#clienteBtn").click();
            return false;
        }
        if (cliente !== undefined && !cliente) {
            toast(`${ic_amarelo} Cliente deve ser informado!`, cor_amarelo);
            $("#clienteBtn").click();
            return false;
        }
        if (!verificarTotalFormas()) {
            toast(`${ic_amarelo} Total das formas de pagamento não corresponde ao valor total!`, cor_amarelo);
            return false;
        }
        $('#staticBackdrop').modal('show');
    });
    function zerarTotais() {
        const zeroBR = 'R$ 0,00';
        $('#subtotal_txt').text(zeroBR);
        $('#total_txt').text(zeroBR);
        $('#custoTotal_txt').text(zeroBR);
        $('#desconto').text(zeroBR);
        $('#acrescimo').text(zeroBR);
        $('#margem_txt').text('0.00%');
        $('#id_subtotal').val('0.00');
        $('#id_total').val('0.00');
        $('#id_vl_form_pgto').val('0.00');
    }
    $("#btnGerarPortas").on("click", function() {
        const selectData = $('#id_tabela_preco').select2('data');
        const tabelaPreco = selectData[0]?.id;
        if (!tabelaPreco) {
            toast(`${ic_amarelo} Tabela de Preço deve ser informada!`, cor_amarelo);
            $("#id_tabela_preco").click();
            return;
        }
        zerarTotais();
        gerarPortas();
        setTimeout(() => {
            inicializarCamposDecimais();
            $('.larg[data-porta="1"]').focus();
        }, 50);
    });
    $(document).on("keydown", "#tabelaPortasResumo input", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            return false;
        }
    });
    $(document).on("keydown", ".larg, .alt", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            return false;
        }
    });
    $("#createForm").on("submit", function(e) {
        e.preventDefault();
        atualizarJSONPortas();
    });
    if (typeof PORTAS_BACKEND !== "undefined" && PORTAS_BACKEND.length) {
        hidratarManagers(PORTAS_BACKEND);
        PORTAS_BACKEND.forEach(p => {
            atualizarTabelaPorta(p.numero);
        });
        atualizarSubtotal();
    }
    $('.modal').on('hidden.bs.modal', function () {$('body').removeClass('modal-open');});
    $(document).on('click', '.editBtn', function () {
        const $tr = $(this).closest('tr');
        const porta = Number($tr.data('porta'));
        const itemId = Number($tr.data('item-id'));
        const isProd = $(this).closest('table').is('#tblProd_' + porta);
        const isAdc  = $(this).closest('table').is('#tblAdc_' + porta);
        if (isProd) {
            prodManager.setEditingItem($tr);
            console.log('DEBUG EDIT:', {porta, itemId, dataPorta: prodManager.data[porta]});
            const item = prodManager.data[porta]?.find(i => i.id === itemId);
            console.log('UNIDADE ITEM:', item);
            if (!item) return;
            $('#editItemModal .modal-title').html(`<i class="fa-solid fa-pen-to-square"></i> Editar Item ${item.cod}`);
            const cod  = item.cod ?? $tr.find('.td-cod').text().trim();
            const desc = item.desc ?? $tr.find('.td-desc').text().trim();
            const unid = item.unid ?? $tr.find('.td-unid').text().trim();
            const vl = item.vl_unit ?? item.vl_unitario ?? parseValor($tr.find('.vl-unit').text()) ?? 0;
            const qtd = item.qtd_final ?? item.qtd ?? parseFloat($tr.find('.qtd-produto').text().replace(',', '.')) ?? 0;
            $('#editCódInput').val(cod);
            $('#editDescInput').val(desc);
            $('#editUnidInput').val(unid);
            $('#editValorItemInput').val(Number(vl).toFixed(2));
            $('#editQtdInput').val(Number(qtd).toFixed(2));
            const modalEdit = new bootstrap.Modal(document.getElementById('editItemModal'));
            modalEdit.show();
        }
        else if (isAdc) {
            prodAdcManager.setEditingItem($tr);
            const item = prodAdcManager.data[porta]?.find(i => i.id === itemId);
            if (!item) return;
            $('#editItemAdcModal .modal-title').html(`<i class="fa-solid fa-pen-to-square"></i> Editar Item ${item.cod}`);
            const cod  = item.cod ?? $tr.find('.td-cod').text().trim();
            const desc = item.desc ?? $tr.find('.td-desc').text().trim();
            const unid = item.unid ?? $tr.find('.td-unid').text().trim();
            const vl   = item.vl_unit ?? parseValor($tr.find('.vl-unit').text()) ?? 0;
            const qtd  = item.qtd_final ?? parseFloat($tr.find('.qtd-produto').text().replace(',', '.')) ?? 0;
            const vlCompra = item.vl_compra ?? parseValor($tr.find('.td-vl-compra').text()) ?? 0;
            $('#editCódAdcInput').val(cod);
            $('#editDescAdcInput').val(desc);
            $('#editUnidAdcInput').val(unid);
            $('#editValorItemAdcInput').val(Number(vl).toFixed(2));
            $('#editQtdAdcInput').val(Number(qtd).toFixed(2));
            $('#editValorCompraItemAdcInput').val(Number(vlCompra).toFixed(2));
            const modalAdc = new bootstrap.Modal(document.getElementById('editItemAdcModal'));
            modalAdc.show();
        }
    });
    $('#saveEditBtn').on('click', function () {
        const { porta, itemId } = prodManager.currentEditing;
        if (!porta || !itemId) return;
        const cells = [$('#editCódInput').val().trim(), $('#editDescInput').val().trim(), $('#editUnidInput').val().trim(), $('#editValorItemInput').val().trim(), $('#editQtdInput').val().trim()];
        prodManager.updateEditingItem(cells);
        const $tr = $(`#tblProd_${porta} tbody tr[data-item-id="${itemId}"]`);
        const qtdManual = parseFloat($('#editQtdInput').val()) || 0;

        // 🔥 SALVA A QUANTIDADE MANUAL
        $tr.data('qtd-manual', qtdManual);

        const item = prodManager.data[porta]?.find(i => i.id === itemId);
        if (item) {
            item.qtd_manual = true;
            item.qtd_final = qtdManual;
        }
        bootstrap.Modal.getInstance(document.getElementById('editItemModal')).hide();
        prodManager.clearEditing();
        setTimeout(async () => {
            await atualizarSubtotal();
            recalcularTotaisPorta(porta);
        }, 500);
    });
    $('#saveEditAdcBtn').on('click', function () {
        const { porta, itemId } = prodAdcManager.currentEditing;
        if (!porta || !itemId) return;
        const item = prodAdcManager.data[porta]?.find(i => i.id === itemId);
        if (!item) return;
        const cod = $('#editCódAdcInput').val().trim();
        const desc = $('#editDescAdcInput').val().trim();
        const unid = $('#editUnidAdcInput').val().trim();
        const vl = parseFloat($('#editValorItemAdcInput').val().replace(',', '.')) || 0;
        const qtd = parseFloat($('#editQtdAdcInput').val().replace(',', '.')) || 0;
        const vl_compra = parseFloat($('#editValorCompraItemAdcInput').val().replace(',', '.')) || 0;
        adicionarAdicionalNaTabela(porta, {cod, desc, unid, qtd, vl, vl_compra, lado: item.lado || '', especifico: item.especifico || ''});
        const $tr = $(`#tblAdc_${porta} tbody tr[data-item-id="${itemId}"]`);
        $tr.data('qtd-manual', qtd);

        if (item) {
            item.qtd_manual = true;
            item.qtd_final = qtd;
        }
        bootstrap.Modal.getInstance(document.getElementById('editItemAdcModal')).hide();
        prodAdcManager.clearEditing();
        setTimeout(async () => {
            await atualizarSubtotal();
            recalcularTotaisPorta(porta);
            atualizarJSONPortas();
        }, 100);
    });
    $('.remQtd').on('click', function () {
        let qtd = parseFloat($('#editQtdInput').val()) || 0;
        if (qtd > 0) $('#editQtdInput').val((qtd - 1).toFixed(2));
    });
    $('.addQtd').on('click', function () {
        let qtd = parseFloat($('#editQtdInput').val()) || 0;
        $('#editQtdInput').val((qtd + 1).toFixed(2));
    });
    $('.remQtdAdc').on('click', function () {
        let qtd = parseFloat($('#editQtdAdcInput').val()) || 0;
        if (qtd > 0) $('#editQtdAdcInput').val((qtd - 1).toFixed(2));
    });
    $('.addQtdAdc').on('click', function () {
        let qtd = parseFloat($('#editQtdAdcInput').val()) || 0;
        $('#editQtdAdcInput').val((qtd + 1).toFixed(2));
    });
    const formaManager = {
        addItem(cells, options = {}) {
            const idx = $('#itensTableForm tbody tr').length + 1;
            const geraParcelas = options.geraParcelas == 1 || options.geraParcelas === true;
            const parcelasExibir = geraParcelas ? cells[2] : '-';
            const diasExibir     = geraParcelas ? cells[3] : '-';
            const parcelas = geraParcelas ? (cells[2] || 1) : 1;
            const dias     = geraParcelas ? (cells[3] || 0) : 0;
            $('#itensTableForm tbody').append(`
                <tr
                    data-forma-id="${options.formaId || ''}"
                    data-valor="${options.valor || 0}"
                    data-parcelas="${parcelas}"
                    data-dias="${dias}"
                    data-gera-parcelas="${geraParcelas ? 1 : 0}"
                    data-troco="${options.troco ? 1 : 0}"
                    data-gateway="${options.gateway || ''}"
                    data-credencial='${JSON.stringify(options.credencial || {}).replace(/'/g, "&apos;")}'
                >
                    <td>${idx}</td>
                    <td>${cells[0]}</td>
                    <td>${cells[1]}</td>
                    <td>${parcelasExibir}</td>
                    <td>${diasExibir}</td>
                    <td>
                        <button class="btn btn-danger btn-sm deleteFormaBtn">
                            <i class="fa-solid fa-trash-can text-white"></i>
                        </button>
                    </td>
                </tr>
            `);
        }
    };
    function addForma(
        formaId,
        formaPgto,
        valor,
        parcelas = 1,
        dias = 0,
        gateway = '',
        geraParcelas = false,
        credenciais = {},
        troco = false
    ) {
        const valorNumero = parseFloat(valor) || 0;
        const valorExibicao = valorNumero.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        const parcelasExibicao = geraParcelas ? parcelas : '-';
        const diasExibicao     = geraParcelas ? dias : '-';
        // 🔥 AQUI ESTÁ A CORREÇÃO PRINCIPAL
        formaManager.addItem(
            [
                formaPgto,
                valorExibicao,
                parcelasExibicao,
                diasExibicao
            ],
            {
                formaId: formaId,
                valor: valorNumero,
                parcelas: parcelas,
                dias: dias,
                gateway: gateway,
                geraParcelas: geraParcelas,
                credencial: credenciais,
                troco: troco
            }
        );
        atualizarSubtotal();
        verificarTotalFormas();
        calcularValorForma();
        somaFormas();
        gerarJSONFormas();
    }
    function toNumberBR(v) {
        return parseFloat(String(v || '0').replace(/\./g, '').replace(',', '.')) || 0;
    }
    function gerarJSONFormas() {
        const formas = [];
        $('#itensTableForm tbody tr').each(function (i) {
            const $row = $(this);
            const forma_id = $row.data('forma-id');
            // 🔥 CORREÇÃO AQUI
            let valorRaw = $row.data('valor');
            if (typeof valorRaw === 'string') {
                valorRaw = valorRaw.replace(/\./g, '').replace(',', '.');
            }
            const valor = parseFloat(valorRaw) || 0;
            const gera_parcelas = !!$row.data('gera-parcelas');
            const parcelas = gera_parcelas ? ($row.data('parcelas') ?? 1) : 1;
            const dias     = gera_parcelas ? ($row.data('dias') ?? 0) : 0;
            const gateway  = ($row.data('gateway') || '').toString().toLowerCase();
            console.log(`Linha ${i + 1}`, {
                forma_id,
                valor,
                parcelas,
                dias,
                gateway,
                gera_parcelas
            });
            if (!forma_id || valor < 0.01) {
                console.warn(`Linha ${i + 1} ignorada`);
                return;
            }
            formas.push({
                forma_id,
                valor: Number(valor.toFixed(2)),
                parcelas,
                dias,
                gateway,
                gera_parcelas
            });
        });
        const json = JSON.stringify(formas);
        $('#id_json_formas_pgto').val(json);
        return formas;
    }
    $('#confirmBtn').on('click', function () {
        gerarJSONFormas();
        const modalConfirm = bootstrap.Modal.getInstance(document.getElementById('staticBackdrop'));
        modalConfirm.hide();
        iniciarLoading();
        setTimeout(() => {
            $('#createForm')[0].submit();
            atualizarJSONPortas();
        }, 200);
    });
    function formaJaExiste(formaId) {
        let existe = false;
        $('#itensTableForm tbody tr').each(function () {
            if ($(this).data('forma-id') == formaId) {
                existe = true;
                return false; // break
            }
        });
        return existe;
    }
    $('#addItemValorFormBtn').on('click', function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        const selectData = $('#id_formas_pgto').select2('data');
        const formaPgto  = selectData[0]?.id;
        const valorStr = $('#id_vl_form_pgto').val();
        const valor    = parseValor(valorStr);
        const parcelas = parseInt($('#id_parcelas').val()) || 1;
        const dias     = parseInt($('#id_dias').val()) || 30;
        if (!formaPgto) {
            toast(`${ic_amarelo} Forma de Pagamento deve ser informada!`, cor_amarelo);
            $("#form_pgtoBtn").click();
            return;
        }
        if (valor <= 0) {
            toast(`${ic_amarelo} Informe um valor válido!`, cor_amarelo);
            return;
        }
        if (formaJaExiste(formaPgto)) {
            toast(`${ic_amarelo} Forma de pagamento já inclusa na tabela!`, cor_amarelo);
            return;
        }
        $.ajax({
            url: `/formas_pgto/forma-pgto-info/${formaPgto}/`, // 🔥 rota correta
            method: "GET",
            success: function (response) {
                console.log(response);

                addForma(
                    response.id,
                    response.descricao,
                    valor,
                    parcelas,
                    dias,
                    response.gateway,
                    response.gera_parcelas,
                    response.credenciais,
                    response.troco
                );
                $('#id_formas_pgto').val(null).trigger('change');

                // (opcional) limpa campos auxiliares
                $('#id_vl_form_pgto').val('');
                $('#id_parcelas').val(1);
                $('#id_dias').val(30);
            }
        });
    });
    $(document).on('click', '.deleteFormaBtn', function () {
        const row = $(this).closest('tr');
        row.remove();
        $('#itensTableForm tbody tr').each(function(i){$(this).find('td:first').text(i + 1);});
        atualizarSubtotal();
        verificarTotalFormas();
        somaFormas();
        gerarJSONFormas();
    });
    $('#addItemProdBtn').on('click', function() {
        const codigo = $('#id_cod_prod').val().trim(); // Assumindo que você tem campos específicos para produtos adicionais
        const descricao = $('#id_desc_prod').val().trim();
        const unidade = $('#id_unidProd').val().trim();
        const valor = parseValor($('#id_vl_prod').val().trim());
        const quantidade = parseFloat($('#id_qtd_prod').val().trim());
        if (!codigo || !descricao || !unidade || isNaN(valor) || isNaN(quantidade) || quantidade <= 0) {
            return alert("Por favor, preencha todos os campos corretamente.");
        }
        prodAdcManager.addItem([codigo, descricao, unidade, valor.toFixed(2), valor.toFixed(2), quantidade.toFixed(2)]);
        $('#id_cod_prod, #id_desc_prod, #id_unidProd, #id_vl_prod, #id_qtd_prod').val('');
        $('#id_cod_prod').focus();
    });
    $('#addItemProdAdcBtn').on('click', function() {
        const codigo = $('#id_cod_prod_adc').val().trim(); // Assumindo que você tem campos específicos para produtos adicionais
        const descricao = $('#id_desc_prod_adc').val().trim();
        const unidade = $('#id_unidProd_adc').val().trim();
        const valor = parseValor($('#id_vl_prod_adc').val().trim());
        const quantidade = parseFloat($('#id_qtd_prod_adc').val().trim());
        if (!codigo || !descricao || !unidade || isNaN(valor) || isNaN(quantidade) || quantidade <= 0) {return alert("Por favor, preencha todos os campos corretamente.");}
        prodAdcManager.addItem([codigo, descricao, unidade, 0.00, valor.toFixed(2), quantidade.toFixed(2), 0.00, (valor * quantidade).toFixed(2)]);
        $('#id_cod_prod_adc, #id_desc_prod_adc, #id_unidProd_adc, #id_vl_prod_adc, #id_qtd_prod_adc').val('');
        $('#id_cod_prod_adc').focus();
    });
    let lastLg = null;
    let lastAt = null;
    $('#prod_servBtn, #adicionaisBtn').on('click', function () {
        let porta = $(this).data("porta");  // ← AQUI TAMBÉM FUNCIONA
        const larg = $(`.larg[data-porta="${porta}"]`).val();
        const alt  = $(`.alt[data-porta="${porta}"]`).val();
        if (!larg || !alt) {
            console.log("Sem largura/altura — não recalculando.");
            return;
        }
        const lg = parseFloat(larg.replace(",", "."));
        const at = parseFloat(alt.replace(",", "."));
        if (lg === lastLg && at === lastAt) {
            console.log("Click sem mudança — não resetando tabelas.");
            return;
        }
        $(`.larg[data-porta="${porta}"], .alt[data-porta="${porta}"]`).blur();
    });
    $('#id_cod_prod').on('blur keydown', function(event) {
        if (event.type === 'blur' || event.key === 'Enter') {
            const productId = $(this).val();
            const tpProduto = $('#id_tp_produto').val(); // Obtém o valor do select
            if (productId.trim() === '') {return;}
            $.ajax({
                url: '/produtos/lista_ajax/', method: 'GET', data: {s: productId, tp: 'cod', tp_prod: 'Principal', tabela_id: getTabelaPreco(), auto: 0},
                success: function(response) {
                    if (response.produtos.length > 0) {
                        const produto = response.produtos[0];
                        $('#id_desc_prod').val(produto.desc_prod);
                        $('#id_unidProduto').val(produto.unidProd);
                        $('#id_vl_compra').val(produto.vl_compra);
                        $('#id_vl_prod').val(produto.vl_prod);
                        if (produto.vl_prod === "0.00" || produto.vl_prod === "") {$('#id_vl_prod').focus();}
                        else {$('#id_qtd_prod').focus();}
                    }
                    else {toast(`${ic_amarelo} Código de produto não encontrado!`, cor_amarelo);}
                }, error: function() {toast(`${ic_vermelho} Erro ao buscar o produto. Tente novamente!`, cor_vermelho);}
            });
        }
    });
    function getFormProdutoByPorta(porta) {return $(`.form-produto[data-porta="${porta}"]`);}
    function getFormAdcByPorta(porta) {return $(`.form-adicional[data-porta="${porta}"]`);}
    function toggleCampoLado($form, produto, isAdicional) {
        if (!isAdicional) return;
        const opcoes = ['Portinhola', 'Alçapão', 'Coluna Removível'];
        const especifico = (produto.especifico || '').trim();
        const $campo = $form.find('.campo-lado-adc');
        const $select = $form.find('.lado-adc');
        if (opcoes.includes(especifico)) {
            $campo.removeClass('d-none');
            $select.val('E');
        } else {
            $campo.addClass('d-none');
            $select.val('');
        }
    }
    function buscarProdutoPorCodigo($input, tipo) {
        const porta = Number($input.data('porta'));
        const cod = $input.val().trim();
        if (!cod) return;
        const isAdicional = tipo === 'Adicional';
        const $form = isAdicional ? getFormAdcByPorta(porta) : getFormProdutoByPorta(porta);
        console.log('🔍 Buscar', tipo, '| Porta:', porta, '| Código:', cod);
        $.ajax({
            url: '/produtos/lista_ajax/', method: 'GET',  data: {s: cod, tp: 'cod', tp_prod: tipo, tabela_id: getTabelaPreco(), auto: 0},
            success(response) {
                if (!response.produtos?.length) {
                    toast(`${ic_amarelo} Código de produto não encontrado!`, cor_amarelo);
                    return;
                }
                const produto = response.produtos[0];
                if (isAdicional) {$form.data('especifico', produto.especifico || '');}
                let map;
                if (isAdicional) {map = {desc: '.desc-prod-adc', unid: '.unid-prod-adc', valor: '.valor-prod-adc', qtd: '.qtd-prod-adc'};}
                else {map = {desc: '.desc-prod', unid: '.unid-prod', valor: '.valor-prod', qtd: '.qtd-prod'};}
                $form.find(map.desc).val(produto.desc_prod);
                $form.find(map.unid).val(produto.unidProd);
                $form.find(map.valor).val(produto.vl_prod.toFixed(2));
                if (isAdicional) {$form.find('.vl-compra-prod-adc').val(produto.vl_compra ? Number(produto.vl_compra).toFixed(2) : '0.00');}
                const $qtd = $form.find(map.qtd);
                $qtd.val('1.00').data('auto', false);
                toggleCampoLado($form, produto, isAdicional);
                $form.find(map.valor).focus();
            },
            error() {toast(`${ic_vermelho} Erro ao buscar o produto. Tente novamente!`, cor_vermelho);}
        });
    }
    $(document).on('blur', '.cod-prod', function () {buscarProdutoPorCodigo($(this), 'Principal');});
    $(document).on('keyup', '.cod-prod', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            buscarProdutoPorCodigo($(this), 'Principal');
        }
    });
    $(document).on('blur', '.cod-prod-adc', function () {buscarProdutoPorCodigo($(this), 'Adicional');});
    $(document).on('keyup', '.cod-prod-adc', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            buscarProdutoPorCodigo($(this), 'Adicional');
        }
    });
    function carregarDadosCliente(clienteId) {
        if (clienteId) {
            $.ajax({
                url: '/clientes/lista_ajax/',  method: 'GET',  data: { term: clienteId },
                success: function(response) {
                    if (response.results && response.results.length > 0) {
                        const cliente = response.results[0];
                        $('#id_cpfCnpj').val(cliente.cpfCnpj);
                        $('#id_email').val(cliente.email);
                        $('#id_tel').val(cliente.tel);
                        $('#id_cep').val(cliente.cep);
                        $('#id_endereco').val(cliente.endereco);
                        $('#id_numero').val(cliente.numero);
                        $('#id_bairro_txt').val(cliente.bairro);
                        $('#id_cidade_txt').val(cliente.cidade);
                        $('#id_uf_txt').val(cliente.uf);
                    }
                }, error: function() {console.error('Erro ao buscar os dados do cliente.');}
            });
        }
    }
    $('#id_cli').on('change', function() {carregarDadosCliente($(this).val());});
    carregarDadosCliente($('#id_cli').val());
    $('#button-addon2').on('click', function() {$('#produtoModal').modal('show');});
    $('#add-produtos').on('click', function() {$('#edProdModal').modal('show');});
    $('#add-produtosP').on('click', function() {$('#edProdModalP').modal('show');});
    $('#edProdModal').on('shown.bs.modal', function () {$('#id_cod_produto').trigger('focus');});
    function controlarPreco() {
        const alt_vl = $("#id_alt_vlP").val();
        $('#id_preco_unitP').prop('disabled', alt_vl !== "Sim");
    }
    function atualizarLabel() {
        const tipo = ($("#id_tipo_desc_acres").val() || '').trim().toLowerCase();
        const operacao = ($("#id_atribuir").val() || '').trim().toLowerCase();
        const vl = parseValor($('#id_preco_unitP').val());
        const qtd = parseFloat($('#id_quantidadeP').val()) || 0;
        const base = vl * qtd;
        const valor = parseValor($('#id_desc_acres').val());
        const $label = $("label[for='id_desc_acres']");
        let prefixo = operacao === "acréscimo" || operacao === "acrescimo"
            ? "Acrésc.:"
            : "Dsct.:";
        if (tipo === "percentual") {
            const convertido = base * (valor / 100);
            $label.text(`${prefixo} R$ ${convertido.toFixed(2)}`);
        }
        else if (tipo === "valor") {
            const convertido = base ? (valor / base) * 100 : 0;
            $label.text(`${prefixo} ${convertido.toFixed(2)}%`);
        }
    }
    function calcularTotal() {
        const vl = parseValor($('#id_preco_unitP').val());
        const qtd = parseFloat($('#id_quantidadeP').val()) || 0;
        const at = ($("#id_atribuir").val() || '').trim().toLowerCase();
        const tipo = ($("#id_tipo_desc_acres").val() || '').trim().toLowerCase();
        const valorExtra = parseValor($('#id_desc_acres').val());
        let total = vl * qtd;
        if (at === "desconto") {
            if (tipo === "valor") {
                total -= valorExtra;
            } else if (tipo === "percentual") {
                total -= total * (valorExtra / 100);
            }
        }
        else if (at === "acréscimo") {
            if (tipo === "valor") {
                total += valorExtra;
            } else if (tipo === "percentual") {
                total += total * (valorExtra / 100);
            }
        }
        if (total < 0) total = 0;
        $('#id_vl_total_preco').val(total.toFixed(2));
    }
    $('#edProdModalP').on('shown.bs.modal', function () {
        atualizarLabel();
        if (!trEditando) {
            $('#id_cod_produtoP').prop('disabled', false);
        }

        setTimeout(() => {
            $('#id_cod_produtoP').trigger('focus');
        }, 50);
        // 🔥 SÓ LIMPA SE NÃO ESTIVER EDITANDO
        if (!trEditando) {
            $('#id_quantidadeP').val('1.00');
            $('#id_preco_unitP').val('0.00');
            $('#id_vl_total_preco').val('0.00');
            $('#id_desc_acres').val('0.00');
        }

        controlarPreco();
    });
    $('#edProdModalP').on('hidden.bs.modal', function () {
        trEditando = null;
        $('#id_cod_produtoP').prop('disabled', false);
    });
    $('#id_quantidadeP, #id_preco_unitP, #id_desc_acres, #id_atribuir, #id_tipo_desc_acres')
    .on('input change keyup', function () {
        calcularTotal();
        atualizarLabel();
    });
    $("#id_tipo_desc_acres").on('change', function () {
        atualizarLabel();
        calcularTotal();
    });
    $('.addQtdP, .remQtdP').on('click', function () {
        setTimeout(calcularTotal, 50);
    });
    $('#id_alt_vlP').on('change', function () {
        const valor = $(this).val();
        if (valor === "Sim") {
            verificarPermissaoAntesDeExecutar(
                'pedidos.alt_vl_ped',
                function () {
                    // ✅ Permitido
                    $('#id_preco_unitP').prop('disabled', false);
                },
                function () {
                    // ❌ Negado
                    $('#id_alt_vlP').val('Não'); // volta pro padrão
                    $('#id_preco_unitP').prop('disabled', true);
                    toast(`${ic_amarelo} Seu usuário não pode alterar valor de produtos em pedidos!`, cor_amarelo);
                }
            );
        } else {
            // Se for "Não", só bloqueia
            $('#id_preco_unitP').prop('disabled', true);
        }
    });

    $('#add-prod, #add-prodP').on('click', function() {$('#produtoModal').modal('show');});
    $('#button-addon3').on('click', function() {$('#produtoAdcModal').modal('show');});
    $('#pesquisar-produtos').on('click', function() {
        const termo = $('#campo-pesquisa-produto').val();
        $.ajax({
            url: '/produtos/lista_ajax/', method: 'GET', data: { s: termo, tp: 'desc', tp_prod: 'Principal', tabela_id: getTabelaPreco(), auto: 0 },
            success: function(response) {
                const tabela = $('#produtos-lista');
                tabela.empty();
                if (response.produtos.length > 0) {
                    response.produtos.forEach(produto => {
                        const row = `
                            <tr>
                                <td style="width: 20px;">
                                    <button class="btn btn-sm btn-dark selecionar-produto" data-id="${produto.id}" data-desc="${produto.desc_prod}" data-unid="${produto.unidProd}" data-vl="${produto.vl_prod}" title="Selecionar" style="margin-left: 9px;">
                                        <i class="fa-regular fa-hand-pointer"></i>
                                    </button>
                                </td>
                                <td>${produto.id}</td><td>${produto.desc_prod}</td><td>${produto.unidProd}</td><td>${produto.estoque_prod}</td><td>${produto.vl_prod}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                }
                else {tabela.append('<tr><td colspan="6">Nenhum produto encontrado.</td></tr>');}
            }, error: function() {}
        });
    });
    $(document).on('click', '.selecionar-produto', function() {
        const id = $(this).data('id');
        const desc = $(this).data('desc');
        const gp = $(this).data('gp');
        const unid = $(this).data('unid');
        const vl = $(this).data('vl');
        $('#id_cod_prod').val(id);
        $('#id_desc_prod').val(desc);
        $('#id_grupoProd').val(gp);
        $('#id_unidProduto').val(unid);
        $('#id_vl_prod').val(vl);
        $('#id_cod_prod').focus();
        $('#produtoModal').modal('hide'); // Fecha o modal após a seleção
    });
    $(document).on('click', '.select-produto', function() {
        const id = $(this).data('id');
        const vl = $(this).data('vl');
        const formsetPrefix = "{{ formset.prefix }}";
        const totalForms = document.getElementById("id_" + formsetPrefix + "-TOTAL_FORMS");
        const formCount = parseInt(totalForms.value);
        const newForm = document.querySelector("tbody tr").cloneNode(true);
        newForm.querySelectorAll("input, select").forEach(function(input) {
            input.name = input.name.replace("-0-", "-" + formCount + "-");
            input.id = input.id.replace("-0-", "-" + formCount + "-");
            if (input.name.includes("produto")) {input.value = id;}
            if (input.name.includes("quantidade")) {input.value = "";}
            if (input.name.includes("preco_unitario")) {input.value = vl;}
        });
        document.querySelector("#tabela-produtos tbody").appendChild(newForm);
        totalForms.value = formCount + 1;
        $('#produtoModal').modal('hide');
    });
    let portaAtiva = null;
    $(document).on('click', '.btn-busca-prod', function () {portaAtiva = $(this).data('porta');});
    $('#pesquisar-produtos-principais').on('click', function() {
        const termo = $('#campo-pesquisa-produto-principal').val();
        $.ajax({
            url: '/produtos/lista_ajax/', method: 'GET', data: { s: termo, tp: 'desc', tp_prod: 'Principal', tabela_id: getTabelaPreco(), auto: 0 },
            success: function(response) {
                const tabela = $('#produtosPrincipais-lista');
                tabela.empty();
                if (response.produtos.length > 0) {
                    response.produtos.forEach(produto => {
                        const estoqueClass = Number(produto.estoque_prod) < 0 ? 'text-danger fw-bold' : 'text-success fw-bold';
                        const row = `
                            <tr>
                                <td style="width: 20px;">
                                    <button class="btn btn-sm btn-dark selecionar-produto-principal" data-id="${produto.id}" data-desc="${produto.desc_prod}" data-unid="${produto.unidProd}" data-vl="${produto.vl_prod}" title="Selecionar" style="margin-left: 9px;">
                                        <i class="fa-regular fa-hand-pointer"></i>
                                    </button>
                                </td>
                                <td>${produto.id}</td><td>${produto.desc_prod}</td><td>${produto.unidProd}</td><td class="${estoqueClass}">${produto.estoque_prod}</td>
                                <td class="fw-bold">${Number(produto.vl_prod || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                }
                else {tabela.append('<tr><td colspan="6">Nenhum produto encontrado.</td></tr>');}
            }, error: function() {}
        });
    });
    $(document).on('click', '.selecionar-produto-principal', function () {
        if (!portaAtiva) return;
        const id = $(this).data('id');
        const desc = $(this).data('desc');
        const unidade = $(this).data('unid');
        const vl = $(this).data('vl');
        $(`.cod-prod[data-porta="${portaAtiva}"]`).val(id);
        $(`.desc-prod[data-porta="${portaAtiva}"]`).val(desc);
        $(`.unid-prod[data-porta="${portaAtiva}"]`).val(unidade);
        $(`.valor-prod[data-porta="${portaAtiva}"]`).val(vl.toFixed(2));
        $(`.cod-prod[data-porta="${portaAtiva}"]`).focus();
        $('#produtoModal').modal('hide');
    });
    $('#produtoModal').on('hidden.bs.modal', function () {portaAtiva = null;});
    let portaAdcAtiva = null;
    $(document).on('click', '.btn-busca-prod-adc', function () {portaAdcAtiva = $(this).data('porta');});
    $('#pesquisar-produtos-adicionais').on('click', function() {
        const termo = $('#campo-pesquisa-produto-adicional').val();
        $.ajax({
            url: '/produtos/lista_ajax/', method: 'GET', data: { s: termo, tp: 'desc', tp_prod: 'Adicional', tabela_id: getTabelaPreco(), auto: 0 },
            success: function(response) {
                const tabela = $('#produtosAdc-lista');
                tabela.empty();
                if (response.produtos.length > 0) {
                    response.produtos.forEach(produto => {
                        const estoqueClass = Number(produto.estoque_prod) < 0 ? 'text-danger fw-bold' : 'text-success fw-bold';
                        const row = `
                            <tr>
                                <td style="width: 20px;">
                                    <button class="btn btn-sm btn-dark selecionar-produto-adicional" data-id="${produto.id}" data-desc="${produto.desc_prod}" data-unid="${produto.unidProd}" data-vl="${produto.vl_prod}" title="Selecionar" style="margin-left: 9px;">
                                        <i class="fa-regular fa-hand-pointer"></i>
                                    </button>
                                </td>
                                <td>${produto.id}</td><td>${produto.desc_prod}</td><td>${produto.unidProd}</td><td class="${estoqueClass}">${produto.estoque_prod}</td>
                                <td class="fw-bold">${Number(produto.vl_prod || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                }
                else {tabela.append('<tr><td colspan="6">Nenhum produto encontrado.</td></tr>');}
            }, error: function() {}
        });
    });
    $(document).on('click', '.selecionar-produto-adicional', function () {
        if (!portaAdcAtiva) return;
        const id = $(this).data('id');
        const desc = $(this).data('desc');
        const unidade = $(this).data('unid');
        const vl = $(this).data('vl');
        $(`.cod-prod-adc[data-porta="${portaAdcAtiva}"]`).val(id);
        $(`.desc-prod-adc[data-porta="${portaAdcAtiva}"]`).val(desc);
        $(`.unid-prod-adc[data-porta="${portaAdcAtiva}"]`).val(unidade);
        $(`.valor-prod-adc[data-porta="${portaAdcAtiva}"]`).val(vl.toFixed(2));
        $(`.cod-prod-adc[data-porta="${portaAdcAtiva}"]`).focus();
        $('#produtoAdcModal').modal('hide');
    });
    $('#produtoAdcModal').on('hidden.bs.modal', function () {portaAdcAtiva = null;});
    var cores = {
        "Preto": "#000000", "Branco": "#FFFFFF", "Amarelo": "#FFFF00", "Vermelho": "#FF0000", "Roxo Açaí": "#6A0DAD", "Azul Pepsi": "#0033A0", "Azul Claro": "#ADD8E6", "Cinza Claro": "#D3D3D3",
        "Cinza Grafite": "#4F4F4F", "Cinza Chumbo": "#5B5B58", "Chumbo": "#8D918D", "Verde": "#008000", "Bege": "#F5F5DC", "Bege Areia": "#D7C9A3", "Marrom": "#8B4513", "Marrom Café": "#4B2E2B",
        "Laranja": "#FFA500", "Azul Royal": "#4169E1", "Azul Marinho": "#000080", "Azul Pepsi": "#004B93", "Verde Musgo": "#556B2F", "Verde Bandeira": "#009739", "Vinho": "#8B0000", "Prata": "#C0C0C0"
    };
    function pintarOptions() {
        $("#id_cor option").each(function () {
            let texto = $(this).text();
            let cor = cores[texto];
            if (cor) {$(this).css({"background-color": cor, "color": isCorEscura(cor) ? "#FFFFFF" : "#000000"});}
        });
    }
    function isCorEscura(hex) {
        hex = hex.replace('#', '');
        let r = parseInt(hex.substr(0, 2), 16);
        let g = parseInt(hex.substr(2, 2), 16);
        let b = parseInt(hex.substr(4, 2), 16);
        let luminancia = (0.299 * r + 0.587 * g + 0.114 * b);
        return luminancia < 140; // limite para considerar escura
    }
    function atualizarCor() {
        var corSelecionada = $("#id_cor").val();
        var novaCor = cores[corSelecionada] || "#FFFFFF";
        $("#id_cor").css({"background-color": novaCor, "color": isCorEscura(novaCor) ? "#FFFFFF" : "#000000"});
    }
    $("#id_cor").on("change", atualizarCor);
    pintarOptions();
    atualizarCor();
    function mudarCampoChavePix() {
        let tipoChave = $('#id_tp_chave').val();
        let inputChavePix = $("#id_chave_pix");
        inputChavePix.unmask(); // Remove máscara anterior
        inputChavePix.prop("readonly", false); // Torna o campo editável por padrão
        inputChavePix.attr("type", "text"); // Volta ao tipo padrão
        if (tipoChave === 'CPF') {inputChavePix.mask("000.000.000-00");}
        else if (tipoChave === 'CNPJ') {inputChavePix.mask("00.000.000/0000-00");}
        else if (tipoChave === 'Telefone') {inputChavePix.mask('(00) 00000-0000');}
        else if (tipoChave === 'E-mail') {inputChavePix.attr("type", "email");}
        else if (tipoChave === 'Chave Aleatória') {inputChavePix.mask('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA', {translation: {'A': { pattern: /[a-fA-F0-9]/ }}, placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"});}
    }
    function atualizarCampo() {
        let tipoPessoa = $("#id_pessoa").val();
        let labelCpfCnpj = $("label[for='id_cpf_cnpj']");
        let labelnome = $("label[for='id_razao_social']");
        let labelapelido = $("label[for='id_fantasia']");
        let labelIE = $("label[for='id_ie']");
        let inputCpfCnpj = $("#id_cpf_cnpj");
        if (tipoPessoa === "Física") {
            labelCpfCnpj.text("CPF*");
            labelnome.text("Nome Completo*");
            labelapelido.text("Apelido*");
            labelIE.text("RG");
            inputCpfCnpj.unmask().mask("000.000.000-00"); // Máscara para CPF
            fecharLoading();
        } else {
            labelCpfCnpj.text("CNPJ*");
            labelnome.text("Razão Social*");
            labelapelido.text("Fantasia*");
            labelIE.text("IE");
            inputCpfCnpj.unmask().mask("00.000.000/0000-00"); // Máscara para CNPJ
        }
    }
    $("#id_cnpj").mask("00.000.000/0000-00");
    atualizarCampo(); // Executa ao carregar a página com valor existente
    $("#id_pessoa").change(atualizarCampo); // Executa ao mudar o valor
    mudarCampoChavePix();
    $("#id_tp_chave").change(mudarCampoChavePix);
    function maskInput(input) {
        setTimeout(function () {
            var v = phoneMask(input.val());
            if (v !== input.val()) {
                input.val(v);
            }
        }, 1);
    }
    function phoneMask(v) {
        let r = v.replace(/\D/g, ""); // Remove tudo que não for número
        if (r.length > 11) {r = r.replace(/^(\d{2})(\d{5})(\d{4}).*/, "($1) $2-$3");}
        else if (r.length === 11) {r = r.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");}
        else if (r.length === 10) {r = r.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");}
        else if (r.length > 2) {r = r.replace(/^(\d{2})(\d{0,5})/, "($1) $2");}
        else if (r.length > 0) {r = r.replace(/^(\d*)/, "($1");}
        return r;
    }
    $("#id_tel").on("input", function () {maskInput($(this));});
    function mascaraFone(phone) {
        let cleanedPhone = phone.replace(/\D/g, '');
        if (cleanedPhone.length > 2) {
            if (cleanedPhone[2] === '8' || cleanedPhone[2] === '9') {
                cleanedPhone = cleanedPhone.slice(0, 2) + '9' + cleanedPhone.slice(2);
                return cleanedPhone.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
            }
            else if (cleanedPhone[2] === '4' || cleanedPhone[2] === '5' || cleanedPhone[2] === '6') {return cleanedPhone.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');}
        }
        return cleanedPhone.replace(/^(\d{2})(\d{4,5})(\d{4})$/, '($1) $2-$3');
    }
    $("#id_cpf_cnpj").on("blur", function () {
        let tipoPessoa = $("#id_pessoa").val();
        let cnpj = $(this).val().replace(/\D/g, ""); // Remove caracteres não numéricos
        if (tipoPessoa === "Jurídica" && cnpj.length === 14) {
            iniciarLoading();
            fetch(`https://open.cnpja.com/office/${cnpj}`).then(response => response.json()).then(data => {
                console.log(data);
                if (data.company) {
                    $('#id_razao_social').val((data.company.name || "").toUpperCase());
                    $('#id_fantasia').val((data.alias || "").toUpperCase());
                }
                if (data.registrations && data.registrations.length > 0) {
                    let ieNumber = data.registrations[0].number || "";
                    if (data.registrations[0].state === "PA") {ieNumber = ieNumber.replace(/^(\d{2})(\d{3})(\d{3})(\d{1})$/, '$1.$2.$3-$4');}
                    $('#id_ie').val(ieNumber);
                }
                let cep = (data.address?.zip || "").replace(/^(\d{5})(\d{3})$/, '$1-$2');
                $('#id_cep').val(cep);
                let endereco = (data.address?.street || "").toUpperCase();
                $('#id_endereco').val(abreviarEndereco(endereco));
                $('#id_numero').val(data.address?.number || "");
                let estado = (data.address?.state || "").toUpperCase();
                let cidade = (data.address?.city ? removeAccents(data.address.city) : "").toUpperCase();
                let bairro = (data.address?.district || "").toUpperCase();
                verificarOuCriarLocalizacao(estado, cidade, bairro).then(response => {
                    if (!response.erro) {
                        let estadoOption = new Option(response.estado_nome, response.estado_id, true, true);
                        $('#id_uf').append(estadoOption).trigger('change');
                        let cidadeOption = new Option(response.cidade_nome, response.cidade_id, true, true);
                        $('#id_cidade').append(cidadeOption).trigger('change');
                        let bairroOption = new Option(response.bairro_nome, response.bairro_id, true, true);
                        $('#id_bairro').append(bairroOption).trigger('change');
                    }
                });
                if (data.phones && data.phones.length > 0) {
                    let telefone = (data.phones[0].area || "") + " " + (data.phones[0].number || "");
                    $('#id_tel').val(mascaraFone(telefone));
                }
                if (data.emails && data.emails.length > 0) {$('#id_email').val(data.emails[0].address || "");}
            }).catch(error => console.error('Erro ao buscar CNPJ:', error)).finally(() => {setTimeout(() => {fecharLoading();}, 500);});
        }
    });
    function atualizarSelect(selector, nome, id) {
        const option = new Option(nome, id, true, true);
        $(selector).append(option).trigger('change');
    }
    $("#id_empresa_login").on("blur", function() {
        let empresaId = $(this).val().trim();
        if (empresaId) {
            iniciarLoading();
            $.ajax({
                url: "/usuarios/buscar_empresa/", method: "GET", data: { id_empresa: empresaId },
                success: function(response) {
                    if (response.success) {
                        let fantasia = response.fantasia ? response.fantasia.toUpperCase() : "";
                        if (fantasia) {
                            $("#fantasia_fantasia").text(fantasia).removeAttr("hidden");
                            setTimeout(() => {
                                $('#id_username').focus();
                            }, 1500);
                            toastErrorShown = false;
                        }
                        else {$("#fantasia_fantasia").attr("hidden", true).text("");}
                    } else {
                        $("#fantasia_fantasia").attr("hidden", true).text("");
                        $('#id_empresa_login').focus();
                        let errorMessage = response.warning || response.error || "ID inexistente na base de dados";
                        let backgroundColor = response.warning ? "linear-gradient(to right, #d58300, #ffc93b)" : "linear-gradient(to right, #ff416c, #ff4b2b)";
                        if (!toastErrorShown) {
                            toastErrorShown = true;
                            Toastify({text: errorMessage, duration: 5000, gravity: "top", position: "center", backgroundColor: backgroundColor, stopOnFocus: true, escapeMarkup: false,}).showToast();
                        }
                    }
                },
                error: function() {
                    $("#fantasia_fantasia").attr("hidden", true).text("");
                    $('#id_empresa_login').focus();
                },
                complete: function() {fecharLoading();}
            });
        } else {
            $("#fantasia_fantasia").attr("hidden", true).text("");
        }
    });
    $("#id_empresa_login").on("input", function() {
        toastErrorShown = false;
        $("#fantasia_fantasia").attr("hidden", true).text("");
    });
    let errorDiv = $(".alert.alert-block.alert-danger");
    if (errorDiv.length) {
        let errorMessage = errorDiv.find("li").text();
        errorDiv.hide();
        Toastify({text: errorMessage, duration: 5000, gravity: "top", position: "center", backgroundColor: "linear-gradient(to right, #ff416c, #ff4b2b)", stopOnFocus: true, escapeMarkup: false}).showToast();
    }
    let messageContainer1 = $("#toast-messages");
    if (messageContainer1.length) {
        let messages = [];
        try {messages = JSON.parse(messageContainer1.attr("data-messages"));}
        catch (e) {
            console.error("Erro ao analisar JSON:", e);
            messages = [];  // ← Corrige o erro
        }
        if (messages && messages.length > 0) {
            messages.forEach(msg => {
                if (msg && msg.text) {
                    Toastify({text: `<span>${msg.text}</span>`, duration: 5000, gravity: "top", position: "center", backgroundColor: "linear-gradient(to right, #ff416c, #ff4b2b)", stopOnFocus: true, escapeMarkup: false,
                        onClick: function () {
                            document.querySelectorAll(".toastify").forEach(el => {
                                el.style.transition = "opacity 0.5s ease-out";
                                el.style.opacity = "0";
                                setTimeout(() => el.remove(), 500);
                            });
                        },
                    }).showToast();
                }
            });
        }
    }
    let messageContainer = $("#django-messages");
    if (messageContainer.length) {
        let messages = JSON.parse(messageContainer.attr("data-messages"));
        messages.forEach(msg => {
            let bgColor, icon;
            switch (msg.tag) {
                case "success":
                    bgColor = "linear-gradient(to right, #00b09b, #96c93d)";
                    icon = `<i class="fa-solid fa-check"></i>`;// Ícone de confirmação (success)
                    break;
                case "error":
                    bgColor = "linear-gradient(to right, #ff416c, #ff4b2b)";
                    icon = `<i class="fa-solid fa-xmark"></i>`;// Ícone de erro (error)
                    break;
                case "warning":
                    bgColor = "linear-gradient(to right, #ff9f00, #ff6f00)";
                    icon = `<i class="fa-solid fa-triangle-exclamation"></i>`; // Ícone de atenção (warning)
                    break;
                case "info":
                    bgColor = "linear-gradient(to right, #02202B, #017AB1)";
                    icon = `<i class="fa-solid fa-exclamation"></i>`; // Ícone de atenção (warning)
                    break;
                default:
                    bgColor = "linear-gradient(to right, #333, #555)";
                    icon = `<i class="fa-solid fa-exclamation"></i>`; // Ícone de informação/exclamação (default)
            }
            Toastify({text: `<span style="display: flex; align-items: center; gap: 8px;"><strong>${icon}</strong> ${msg.text}</span>`, duration: 5000, gravity: "top", position: "center", backgroundColor: bgColor, stopOnFocus: true, escapeMarkup: false,
                onClick: function () {
                    let toastElements = document.querySelectorAll(".toastify");
                    toastElements.forEach(el => {
                        el.style.transition = "opacity 0.5s ease-out";
                        el.style.opacity = "0";
                        setTimeout(() => el.remove(), 500);
                    });
                },
            }).showToast();
        });
    }
    $(".copiar").on("click", function () {
        let link = $(this).closest(".btn-group").find(".link-rillpay").attr("href");
        if (!link) {
            console.error("Link não encontrado!");
            return; // Se o link não for encontrado, sair da função
        }
        if (navigator.clipboard) {
            navigator.clipboard.writeText(link).then(() => {
                toast(`${ic_verde} Link copiado!`, cor_verde);
            }).catch(err => console.error("Erro ao copiar: ", err));
        } else {
            let tempInput = $("<input>");
            $("body").append(tempInput);
            tempInput.val(link).select();
            document.execCommand("copy");
            tempInput.remove();
            toast(`${ic_verde} Link copiado!`, cor_verde);
        }
    });
    document.addEventListener("DOMContentLoaded", function() {
        var link = document.createElement("link");
        link.rel = "shortcut icon";
        link.href = "https://allitec.pythonanywhere.com/static/img/favicon.ico";
        link.type = "image/x-icon";
        document.head.appendChild(link);
    });
    $('#doc-botao').on('mouseenter', function () {$('#icone-botao').css('color', 'white');});
    $('#doc-botao').on('mouseleave', function () {$('#icone-botao').css('color', 'black');});
    const $checkbox = $("#toggle-data-agendamento");
    const $dataAgendamento = $("#id_data_agendamento");
    $checkbox.change(function () {
        if ($(this).is(":checked")) {$dataAgendamento.prop("disabled", false);}
        else {$dataAgendamento.prop("disabled", true).val("");}
    });
    function updateMassChangesButton() {
        const taskCheckboxes = $(".task-checkbox");
        const massChangesButton = $("#update-selected");
        if (!massChangesButton.length) {
            console.warn("O botão 'update-selected' não foi encontrado.");
            return;
        }
        const anyChecked = taskCheckboxes.is(":checked");
    }
    function updateMassChangesButtonXML() {
        const taskCheckboxes = $(".task-checkbox-xml");
        const massChangesButton = $("#update-selected-xml");
        if (!massChangesButton.length) {
            console.warn("O botão 'update-selected-xml' não foi encontrado.");
            return;
        }
        const anyChecked = taskCheckboxes.is(":checked");
        massChangesButton.prop("disabled", !anyChecked);
    }
    // Marca ou desmarca todos
    function toggleSelectAll(forceCheck = null) {
        const selectAllCheckbox = $("#select-all");
        const taskCheckboxes = $(".task-checkbox");
        const isChecked = forceCheck !== null ? forceCheck : selectAllCheckbox.is(":checked");
        selectAllCheckbox.prop("indeterminate", false);
        selectAllCheckbox.prop("checked", isChecked);
        taskCheckboxes.prop("checked", isChecked);
        updateMassChangesButton();
    }
    function toggleSelectAllXML(forceCheck = null) {
        const selectAllCheckbox = $("#select-all-xml");
        const taskCheckboxes = $(".task-checkbox-xml");
        const isChecked = forceCheck !== null ? forceCheck : selectAllCheckbox.is(":checked");
        selectAllCheckbox.prop("indeterminate", false);
        selectAllCheckbox.prop("checked", isChecked);
        taskCheckboxes.prop("checked", isChecked);
        updateMassChangesButtonXML();
    }
    // Clicar em qualquer parte do <th> alterna o checkbox principal
    $("th:has(#select-all)").on("click", function (e) {
        const checkbox = $("#select-all");
        if ($(e.target).is("#select-all")) return;
        const shouldCheck = !checkbox.prop("checked");
        toggleSelectAll(shouldCheck);
    });
    $("th:has(#select-all-xml)").on("click", function (e) {
        const checkbox = $("#select-all-xml");
        if ($(e.target).is("#select-all-xml")) return;
        const shouldCheck = !checkbox.prop("checked");
        toggleSelectAllXML(shouldCheck);
    });
    // Clique direto no checkbox do thead (mesma lógica)
    $("#select-all").on("click", function (e) {
        e.stopPropagation(); // Evita duplicar clique
        toggleSelectAll($(this).is(":checked"));
    });
    $("#select-all-xml").on("click", function (e) {
        e.stopPropagation(); // Evita duplicar clique
        toggleSelectAllXML($(this).is(":checked"));
    });
    // Alterna um checkbox individual (tbody)
    function toggleTaskCheckbox(cell) {
        const checkbox = $(cell).find("input[type='checkbox']");
        if (checkbox.length) {
            checkbox.prop("checked", !checkbox.is(":checked"));
            checkIfAllSelected();
            updateMassChangesButton();
        }
    }
    function toggleTaskCheckboxXML(cell) {
        const checkbox = $(cell).find("input[type='checkbox']");
        if (checkbox.length) {
            checkbox.prop("checked", !checkbox.is(":checked"));
            checkIfAllSelectedXML();
            updateMassChangesButtonXML();
        }
    }
    // Atualiza o estado do checkbox "selecionar todos"
    function checkIfAllSelected() {
        const selectAllCheckbox = $("#select-all");
        const taskCheckboxes = $(".task-checkbox");
        const total = taskCheckboxes.length;
        const checked = taskCheckboxes.filter(":checked").length;
        if (checked === total) {
            selectAllCheckbox.prop("checked", true);
            selectAllCheckbox.prop("indeterminate", false);
        } else if (checked === 0) {
            selectAllCheckbox.prop("checked", false);
            selectAllCheckbox.prop("indeterminate", false);
        }
        else {selectAllCheckbox.prop("indeterminate", true);}
    }
    function checkIfAllSelectedXML() {
        const selectAllCheckbox = $("#select-all-xml");
        const taskCheckboxes = $(".task-checkbox-xml");
        const total = taskCheckboxes.length;
        const checked = taskCheckboxes.filter(":checked").length;
        if (checked === total) {
            selectAllCheckbox.prop("checked", true);
            selectAllCheckbox.prop("indeterminate", false);
        } else if (checked === 0) {
            selectAllCheckbox.prop("checked", false);
            selectAllCheckbox.prop("indeterminate", false);
        }
        else {selectAllCheckbox.prop("indeterminate", true);}
    }
    $(".form-check-label").click(function (e) {
        e.preventDefault();
        const switchInput = $("#" + $(this).attr("for"));
        switchInput.prop("checked", !switchInput.is(":checked"));
    });
    window.toggleSelectAll = toggleSelectAll;
    window.toggleTaskCheckbox = toggleTaskCheckbox;
    window.checkIfAllSelected = checkIfAllSelected;
    window.updateMassChangesButton = updateMassChangesButton;
    window.toggleSelectAllXML = toggleSelectAllXML;
    window.toggleTaskCheckboxXML = toggleTaskCheckboxXML;
    window.checkIfAllSelectedXML = checkIfAllSelectedXML;
    window.updateMassChangesButtonXML = updateMassChangesButtonXML;
    function closeStaticBackdrop() {
        var modalInstance = bootstrap.Modal.getInstance($("#staticBackdrop")[0]);
        if (modalInstance) modalInstance.hide();
        $("body").removeClass("modal-open");
        $(".modal-backdrop").remove();
        $("body").css({overflow: "", paddingRight: ""});
    }
    // Botão "Não" no modal 'staticBackdrop'
    $("#btnRecusa").on("click", function () {closeStaticBackdrop();});
    // Modal de filial
    $(".btn-delete").on("click", function() {
        let orcamentoId = $(this).attr("data-orcamento-id");
        let modalDelete = new bootstrap.Modal($("#modal-" + orcamentoId)[0]); // ID correto do modal
        modalDelete.show();
    });
    $(".confirm-delete").on("click", function() {
        let filialId = $(this).attr("data-orcamento-id");
        let modalMenu = $("#menuModal" + filialId)[0];
        let modalDelete = $("#modalLabel" + filialId)[0];
        let modalMenuInstance = bootstrap.Modal.getInstance(modalMenu);
        let modalDeleteInstance = bootstrap.Modal.getInstance(modalDelete);
        if (modalMenuInstance) modalMenuInstance.hide();
        if (modalDeleteInstance) modalDeleteInstance.hide();
    });
    $(".btn-cancel").on("click", function() {
        let modalDelete = bootstrap.Modal.getInstance($(this).closest(".modal")[0]);
        if (modalDelete) modalDelete.hide();
    });
    $(document).on("keydown", function(event) {
        let modalConfirm = $(".modal.show[id^='modalLabel']");
        if (!modalConfirm.length) return;
        if (event.key.toLowerCase() === "s") {modalConfirm.find(".confirm-delete").trigger("click");}
        else if (event.key.toLowerCase() === "n") {modalConfirm.find(".btn-cancel").trigger("click");}
    });
    $(document).on("click", "#botoes-modal", function () {
        var actionType = $(this).data("id"); // Identifica a ação associada ao botão
        var menuModal = bootstrap.Modal.getInstance($("#menuModal" + actionType)[0]);
        var docModal = bootstrap.Modal.getInstance($("#documentModal" + actionType)[0]);// Obtem o modal atualmente aberto
        if (menuModal) {menuModal.hide();}
        if (docModal) {docModal.hide();}
    });
    $("#staticBackdrop").on("keydown", function (e) {
        var keyCode = e.which || e.keyCode;
        if (keyCode === 83) {$("#confirmBtn").click();}
        else if (keyCode === 78 || keyCode === 27) {closeStaticBackdrop();}
    });
    $("[id^='modal-']").on("keydown", function (e) {
        const key = e.which || e.keyCode;
        if (key === 83) {$("#confirmBtn").click();}
        else if (key === 78 || key === 27) {closeStaticBackdrop();}
    });
    // Função de Desconto - Orçamentos
    function extrairNumero(str) {return parseFloat(str.replace('R$ ', '').replace(/\./g, '').replace(',', '.').trim()) || 0;}
    // Função de cálculo do desconto e atualização do auxiliar
    function calcularDescontoAtualizarAuxiliar() {
        let tipo_desconto = $('#tipo_desconto').val();
        let $campo = $('#campo_desconto');
        let campoDigitado = $campo.val().trim();
        // Ctrl + A + Delete → força 0.00 no input
        if (campoDigitado === '') {
            $campo.val('0.00');
            campoDigitado = '0';
        }
        campoDigitado = campoDigitado.replace(',', '.');
        let campo_desconto = parseFloat(campoDigitado);
        if (isNaN(campo_desconto)) {
            campo_desconto = 0;
            $campo.val('0.00');
        }
        let subtotal_orcamento = extrairNumero($('#subtotal_txt').text());
        let labelNomeCampo = $("label[for='campo_desconto']");
        let labelNomeCampoAuxiliar = $("label[for='auxiliar_desconto']");
        let simboloInputCampo = $("#simbolo");
        let simboloInputCampoAuxiliar = $("#simboloAuxiliar");
        if (subtotal_orcamento === 0) {
            $('#auxiliar_desconto').val('0.00');
            return 0;
        }
        if (tipo_desconto === "valor") {
            labelNomeCampo.text("Valor:");
            simboloInputCampo.text("R$");
            labelNomeCampoAuxiliar.text("Percentual:");
            simboloInputCampoAuxiliar.text("%");
            let percentual = (campo_desconto / subtotal_orcamento) * 100;
            $('#auxiliar_desconto').val(isNaN(percentual) ? '0.00' : percentual.toFixed(2));
            return campo_desconto;
        } else {
            labelNomeCampo.text("Percentual:");
            simboloInputCampo.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliar.text("R$");
            let valorCalculado = (subtotal_orcamento * campo_desconto) / 100;
            $('#auxiliar_desconto').val(isNaN(valorCalculado) ? '0.00' : valorCalculado.toFixed(2));
            return valorCalculado;
        }
    }
    $("#campo_desconto, #tipo_desconto").on("input keyup change", function () {calcularDescontoAtualizarAuxiliar();});
    // Evento ao abrir o modal
    $('#modalDesconto').on('shown.bs.modal', function () {$('#tipo_desconto').focus();});
    // Evento botão confirmar
    $('#confirmarDesconto').on('click', function () {
        let desconto = calcularDescontoAtualizarAuxiliar();
        desconto = parseFloat(desconto) || 0;
        $('#id_desconto').val(desconto.toFixed(2));
        $('#desconto_txt').text('R$ ' + desconto.toLocaleString('pt-BR', {minimumFractionDigits: 2,  maximumFractionDigits: 2}));
        $('#modalDesconto').modal('hide');
        atualizarSubtotal();
    });
    // Função de Acréscimo - Orçamentos
    function calcularAcrescimoAtualizarAuxiliar() {
        let tipo_acrescimo = $('#tipo_acrescimo').val();
        let $campo = $('#campo_acrescimo');
        let campoDigitado = $campo.val().trim();
        // Ctrl + A + Delete → força 0.00 no input
        if (campoDigitado === '') {
            $campo.val('0.00');
            campoDigitado = '0';
        }
        campoDigitado = campoDigitado.replace(',', '.');
        let campo_acrescimo = parseFloat(campoDigitado);
        if (isNaN(campo_acrescimo)) {
            campo_acrescimo = 0;
            $campo.val('0.00');
        }
        let subtotal_orcamento = extrairNumero($('#subtotal_txt').text());
        let labelNomeCampo = $("label[for='campo_acrescimo']");
        let labelNomeCampoAuxiliar = $("label[for='auxiliar_acrescimo']");
        let simboloInputCampoAc = $("#simboloAc");
        let simboloInputCampoAuxiliarAc = $("#simboloAuxiliarAc");
        if (subtotal_orcamento === 0) {
            $('#auxiliar_acrescimo').val('');
            return 0;
        }
        if (tipo_acrescimo === "valor") {
            labelNomeCampo.text("Valor:");
            simboloInputCampoAc.text("R$");
            labelNomeCampoAuxiliar.text("Percentual:");
            simboloInputCampoAuxiliarAc.text("%");
            let percentual = (campo_acrescimo / subtotal_orcamento) * 100;
            $('#auxiliar_acrescimo').val(isNaN(percentual) ? '0.00' : percentual.toFixed(2));
            return campo_acrescimo;
        } else {
            labelNomeCampo.text("Percentual:");
            simboloInputCampoAc.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliarAc.text("R$");
            let valorCalculado = ((subtotal_orcamento * campo_acrescimo) / 100);
            $('#auxiliar_acrescimo').val(isNaN(valorCalculado) ? '0.00' : valorCalculado.toFixed(2));
            return valorCalculado;
        }
    }
    $("#campo_acrescimo, #tipo_acrescimo").on("input keyup change", function () {calcularAcrescimoAtualizarAuxiliar();});
    // Evento ao abrir o modal
    $('#modalAcrescimo').on('shown.bs.modal', function () {$('#tipo_acrescimo').focus();});
    // Evento botão confirmar
    $('#confirmarAcrescimo').on('click', function () {
        let acrescimo = Number(calcularAcrescimoAtualizarAuxiliar());
        if (isNaN(acrescimo) || acrescimo === undefined || acrescimo === null) {acrescimo = 0;}
        $('#id_acrescimo').val(acrescimo.toFixed(2));
        $('#acrescimo_txt').text('R$ ' + acrescimo.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2}));
        $('#modalAcrescimo').modal('hide');
        atualizarSubtotal();
    });
    $('#exampleModal').on('shown.bs.modal', function () {$('#cid_emp').focus();});
    $('#openModalBtn1').click(function () {
        $('#staticBackdrop2').modal('show');
        $('#staticBackdrop2').on('shown.bs.modal', function () {$(this).focus();});
    });
    $('#confirmBtn, #confirmBtn1').click(function () {
        $('#staticBackdrop2').modal('hide');
        $('#gerarVisitasModal').modal('hide');
    });
    $('#btnRecusa1').click(function () {
        $('#staticBackdrop2').modal('hide');
        $('#gerarVisitasModal').modal('show');
    });
    $('#staticBackdrop2').on("keydown", function (e) {
        var keyCode = e.which || e.keyCode;
        if (keyCode === 83) {$("#confirmBtn1").click();}
        else if (keyCode === 78 || keyCode === 27) {$("#btnRecusa1").click();}
    });
    $('#logo-preview').on('click', function() {$('#id_logo').click();});
    $('#id_logo').on('change', function(event) {
        var reader = new FileReader();
        reader.onload = function(e) {$('#logo-preview').attr('src', e.target.result);};
        reader.readAsDataURL(event.target.files[0]);  // Lê o arquivo selecionado
    });
    $('#tabelas-lista').addClass('table-hover');
    $('.form-control').addClass('form-control-sm');
    $('.form-select').addClass('form-select-sm');
    $("#data-btn").addClass('btn-sm');
    function verificarEstadoUsarData() {
        const usarDataAtivo = $('#usar-data').val() === 'Sim';
        $('#data, #data_inicio, #data_fim, #data_inicio1, #data_fim1').prop('disabled', !usarDataAtivo);
    }
    function verificarBtnPintura() {
        const ativarPintura = $('#id_pintura').val() === 'Sim';
        $('#id_cor').prop('disabled', !ativarPintura);
    }
    verificarEstadoUsarData();
    verificarBtnPintura();
    verificarEstadoSwitch('#switchData', '#dtVisita, #pxVisita');
    verificarEstadoSwitch('#switchIdSis', '#prin');
    verificarEstadoSwitch('#switchIdSis1', '#prin1');
    $('#usar-data').change(verificarEstadoUsarData);
    $('#id_pintura').change(verificarBtnPintura);
    $('#switchData').change(function () {verificarEstadoSwitch('#switchData', '#dtVisita, #pxVisita');});
    $('#switchIdSis').change(function () {verificarEstadoSwitch('#switchIdSis', '#prin');});
    $('#switchIdSis1').change(function () {verificarEstadoSwitch('#switchIdSis1', '#prin1');});
    function verificarEstadoSwitch(selector, target) {$(target).prop('disabled', !$(selector).prop('checked'));}
    // Inicializa o estado ao carregar a página
    verificarEstadoSwitch('#switchEmp', '#unidade1');
    verificarEstadoSwitch('#switchSit', '#grupo1');
    verificarEstadoSwitch('#switchMarca', '#marca1');
    verificarEstadoSwitch('#switchSituacao', '#situacao1');
    $('#switchEmp').change(function () {verificarEstadoSwitch('#switchEmp', '#unidade1');});
    $('#switchSit').change(function () {verificarEstadoSwitch('#switchSit', '#grupo1');});
    $('#switchMarca').change(function () {verificarEstadoSwitch('#switchMarca', '#marca1');});
    $('#switchSituacao').change(function () {verificarEstadoSwitch('#switchSituacao', '#situacao1');});
    // Ao clicar no label, marca/desmarca o switch e dispara o change para atualizar o campo
    $('label[for="switchEmp"], label[for="switchSit"], label[for="switchMarca"], label[for="switchSituacao"]').on('click', function () {
        const switchId = $(this).attr('for');
        setTimeout(() => {
            let target;
            if (switchId === 'switchEmp') target = '#unidade1';
            else if (switchId === 'switchSit') target = '#grupo1';
            else if (switchId === 'switchMarca') target = '#marca1';
            else if (switchId === 'switchSituacao') target = '#situacao1';
            verificarEstadoSwitch('#' + switchId, target);
        }, 10);
    });
    $(document).on('click', '#pesquisar-produtos, #pesquisar-produtos-adicionais, #button-addon3, #button-addon2, .selecionar-produto-adicional, .selecionar-produto', function(e) {
        e.preventDefault();
        $("#id_preco_unit").focus();
    });
    $('#voltarBtn').click(function(e) {
        e.preventDefault();
        fecharLoading(); // Esconde o modal
        $(this).prop('disabled', true);
        var previousPage = document.referrer;
        if (previousPage) {setTimeout(function() {window.location.href = previousPage;}, 300);}
        else {setTimeout(function() {window.location.href = '/lista/';}, 300);}
    });
    $(window).on('beforeunload', function() {iniciarLoading();});
    $(window).on('load', function() {fecharLoading();});
    $('#select-all').on('click', function() {
        var checkboxes = $('input[name="multi"]');
        checkboxes.prop('checked', this.checked);
        toggleUpdateButton();
    });
    $('.task-checkbox').on('change', toggleUpdateButton);
    $('.task-checkbox-xml').on('change', toggleUpdateButtonXML);
    function toggleUpdateButton() {
        var selectedCheckboxes = $('.task-checkbox:checked');
    }
    function toggleUpdateButtonXML() {
        var selectedCheckboxes = $('.task-checkbox-xml:checked');
        $('#update-selected-xml').prop('disabled', selectedCheckboxes.length === 0);
    }
    $('#update-selected').on('click', function() {
        var selectedCheckboxes = $('.task-checkbox:checked');
        var multiIds = selectedCheckboxes.map(function() {return this.value;}).get();
        var container = $('#multi-hidden-container');
        container.empty();
        $.each(multiIds, function(index, id) {
            var input = $('<input>').attr({type: 'hidden', name: 'multi', value: id});
            container.append(input);
        });
        $('#selected-count').text(multiIds.length);
    });
    $('#update-selected-xml').on('click', function() {
        var selectedCheckboxes = $('.task-checkbox-xml:checked');
        var multiIds = selectedCheckboxes.map(function() {return this.value;}).get();
        var container = $('#multi-hidden-container');
        container.empty();
        $.each(multiIds, function(index, id) {
            var input = $('<input>').attr({type: 'hidden', name: 'multi', value: id});
            container.append(input);
        });
        $('#selected-count').text(multiIds.length);
    });
    $('#mdAttTbPreco').on('click', function() {
        var selectedCheckboxes = $('.task-checkbox:checked');
        var multiIds = selectedCheckboxes.map(function() {return this.value;}).get();
        var container = $('#multi-hidden-cont');
        container.empty();
        $.each(multiIds, function(index, id) {
            var input = $('<input>').attr({type: 'hidden', name: 'prod-prec', value: id});
            container.append(input);
        });
        $('#selected-count').text(multiIds.length);
    });
    //Consulta de CNPJ e CEP
    function mascaraFone(phone) {
        let cleanedPhone = phone.replace(/\D/g, '');
        if (cleanedPhone.length > 2) {
            if (cleanedPhone[2] === '8' || cleanedPhone[2] === '9') {
                cleanedPhone = cleanedPhone.slice(0, 2) + '9' + cleanedPhone.slice(2);
                return cleanedPhone.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
            }
            else if (cleanedPhone[2] === '4' || cleanedPhone[2] === '5' || cleanedPhone[2] === '6') {return cleanedPhone.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');}
        }
        return cleanedPhone.replace(/^(\d{2})(\d{4,5})(\d{4})$/, '($1) $2-$3');
    }
    function removeAccents(str) {
        const accents = [{base: 'a', letters: /[áàãâä]/g}, {base: 'e', letters: /[éèêë]/g}, {base: 'i', letters: /[íìîï]/g}, {base: 'o', letters: /[óòõôö]/g}, {base: 'u', letters: /[úùûü]/g}, {base: 'c', letters: /[ç]/g}, {base: 'n', letters: /[ñ]/g}];
        accents.forEach(function(accent) {str = str.replace(accent.letters, accent.base);});
        return str;
    }
    // API De Consulta CNPJ Com Inscrição Estadual
    function abreviarEndereco(endereco) {
        const substituicoes = {'AVENIDA': 'AV.', 'TRAVESSA': 'TV.', 'RUA': 'R.', 'RODOVIA': 'ROD.', 'ESTRADA': 'EST.', 'ALAMEDA': 'AL.', 'LARGO': 'LG.', 'PRACA': 'PC.', 'PRAÇA': 'PC.', 'VILA': 'VL.'};
        let enderecoFormatado = endereco.toUpperCase();
        for (let termo in substituicoes) {
            const regex = new RegExp(`^${termo}\\b`, 'i');
            if (regex.test(enderecoFormatado)) {
                enderecoFormatado = enderecoFormatado.replace(regex, substituicoes[termo]);
                break; // Substitui apenas o primeiro termo encontrado no início
            }
        }
        return enderecoFormatado;
    }
    $('#id_cnpj').on('blur', function(e) {
        let cnpj = $(this).val().replace(/\D/g, '');
        iniciarLoading();
        fetch(`https://open.cnpja.com/office/${cnpj}`).then(response => response.json()).then(data => {
            console.log(data);
            if (data.company) {
                $('#id_razao_social').val((data.company.name || "").toUpperCase());
                $('#id_fantasia').val((data.alias || "").toUpperCase());
            }
            let estado = (data.address.state || "").toUpperCase();
            let cidade = (data.address.city ? removeAccents(data.address.city) : "").toUpperCase();
            let bairro = (data.address.district || "").toUpperCase();
            $('#id_cep').val((data.address.zip || "").replace(/^(\d{5})(\d{3})$/, '$1-$2'));
            $('#id_endereco').val(abreviarEndereco((data.address.street || "").toUpperCase()));
            $('#id_numero').val(data.address.number || "");
            verificarOuCriarLocalizacao(estado, cidade, bairro).then(response => {
                if (!response.erro) {
                    let estadoOption = new Option(response.estado_nome, response.estado_id, true, true);
                    $('#id_uf_emp, #id_uf').append(estadoOption).trigger('change');
                    let cidadeOption = new Option(response.cidade_nome, response.cidade_id, true, true);
                    $('#id_cidade_emp, #id_cidade_fil').append(cidadeOption).trigger('change');
                    let bairroOption = new Option(response.bairro_nome, response.bairro_id, true, true);
                    $('#id_bairro_emp, #id_bairro_fil, #id_bairro').append(bairroOption).trigger('change');
                }
            });
            if (data.phones && data.phones.length > 0) {$('#id_tel, #id_contato_administrador').val(mascaraFone(data.phones[0].area + " " + data.phones[0].number || ""));}
            if (data.emails && data.emails.length > 0) {$('#id_email, #id_email_administrador').val(data.emails[0].address || "");}
            $('#id_cnae_cod').val(data.mainActivity.id || "");
            $('#id_cnae_desc').val((data.mainActivity.text || "").toUpperCase());
            if (data.company.members?.length > 0) {$('#id_administrador').val((data.company.members[0].person.name || "").toUpperCase());}
        }).catch(error => console.error('Erro ao buscar CNPJ:', error)).finally(() => {setTimeout(() => {fecharLoading();}, 2000);});
    });
    function listen() {
        const options = {method: "GET", mode: "cors", cache: "default"};
        $('#id_cep').on('blur', function() {
            let cep = $(this).val().replace("-", "").trim();
            if (cep.length < 8) {
                console.warn("CEP inválido.");
                return;
            }
            iniciarLoading();
            fetch(`https://viacep.com.br/ws/${cep}/json/`, options).then(response => response.json()).then(data => {
                if (data.erro) {
                    console.error("CEP não encontrado.");
                    setTimeout(() => fecharLoading(), 500);
                    return;
                }
                console.log(data);
                const estado = (data.uf || "").toUpperCase();
                const cidade = (data.localidade ? removeAccents(data.localidade) : "").toUpperCase();
                const bairro = (data.bairro || "").toUpperCase();
                verificarOuCriarLocalizacao(estado, cidade, bairro).then(response => {
                    if (!response.error) {
                        atualizarSelect('#id_uf', response.estado_nome, response.estado_id);
                        atualizarSelect('#id_cidade, #id_cidade_fil', response.cidade_nome, response.cidade_id);
                        atualizarSelect('#id_bairro, #id_bairro_fil', response.bairro_nome, response.bairro_id);
                    }
                    setTimeout(() => fecharLoading(), 500); // ✅ delay de 500ms
                })
                .catch(error => {
                    console.error('Erro na verificação de localização:', error);
                    setTimeout(() => fecharLoading(), 500);
                });
                $('#id_endereco').val((data.logradouro || "").toUpperCase());
                $('#id_numero').val((data.numero || "").toUpperCase());
                $('#id_complem').val((data.complemento ? removeAccents(data.complemento) : "").toUpperCase());
                $('#id_bairro_emp').val(bairro);
                $('#id_cidade_emp').val(cidade);
                $('#id_uf_emp').val(estado);
            })
            .catch(error => {
                console.error('Erro ao buscar CEP:', error);
                setTimeout(() => fecharLoading(), 500);
            });
        });
    }
    function atualizarSelect(selector, nome, id) {
        const option = new Option(nome, id, true, true);
        $(selector).append(option).trigger('change');
    }
    function init() {listen();}
    $(document).ready(init);
    var endSecao = $('#enderecos');
    function hideAllSections1() {$('.form-section').hide();}
    function updateButtonStyle1(activeBt, bt1, bt2, bt3, bt4) {
        activeBt?.addClass('btn-ativo').removeClass('btn-inativo');
        bt1?.removeClass('btn-ativo btn-inativo');
        bt2?.removeClass('btn-ativo btn-inativo');
        bt3?.removeClass('btn-ativo btn-inativo');
        bt4?.removeClass('btn-ativo btn-inativo');
    }
    function showSection1(sectionId, activeBt, bt1, bt2, bt3, bt4) {
        hideAllSections1();
        $('#' + sectionId).show();
        updateButtonStyle1(activeBt, bt1, bt2, bt3, bt4);
    }
    hideAllSections1();
    $(endSecao).show();
    const endBt = $('#endBtn');
    const fatuBt = $('#faturBtn');
    const compBt = $('#complBtn');
    const dadosRespBt = $('#dadosRespBtn');
    const financBt = $('#financBtn');
    $(endBt).on('click', function() {showSection1('enderecos', endBt, fatuBt, compBt, dadosRespBt, financBt);});
    $(fatuBt).on('click', function() {showSection1('faturamentos', fatuBt, endBt, compBt, dadosRespBt, financBt);});
    $(compBt).on('click', function() {showSection1('complementos', compBt, endBt, fatuBt, dadosRespBt, financBt);});
    $(dadosRespBt).on('click', function() {showSection1('dadosResponsavel', dadosRespBt, endBt, fatuBt, compBt, financBt);});
    $(financBt).on('click', function() {showSection1('financeiros', financBt, endBt, fatuBt, compBt, dadosRespBt);});
    // Seções do Formulário de Orçamentos
    var clienteSecao = $('#clientes');
    function hideAllSections() {$('.form-section').hide();}
    function updateButtonStyle(activeBtn, btn1, btn2, btn3, btn4) {
        activeBtn.addClass('btn-ativo').removeClass('btn-inativo');
        btn1.removeClass('btn-ativo btn-inativo');
        btn2.removeClass('btn-ativo btn-inativo');
        btn3.removeClass('btn-ativo btn-inativo');
        btn4.removeClass('btn-ativo btn-inativo');
    }
    function showSection(sectionId, activeBtn, btn1, btn2, btn3, btn4) {
        hideAllSections();
        $('#' + sectionId).show();
        updateButtonStyle(activeBtn, btn1, btn2, btn3, btn4);
    }
    hideAllSections();
    $(clienteSecao).show();
    const medidasBtn = $('#medidasBtn');
    const clienteBtn = $('#clienteBtn');
    const prod_servBtn = $('#prod_servBtn');
    const adicionaisBtn = $('#adicionaisBtn');
    const form_pgtoBtn = $('#form_pgtoBtn');
    $(medidasBtn).on('click', function() {showSection('medidas', medidasBtn, clienteBtn, prod_servBtn, adicionaisBtn, form_pgtoBtn);});
    $(clienteBtn).on('click', function() {showSection('clientes', clienteBtn, medidasBtn, prod_servBtn, adicionaisBtn, form_pgtoBtn);});
    $(prod_servBtn).on('click', function() {showSection('prod_serv', prod_servBtn, clienteBtn, medidasBtn, adicionaisBtn, form_pgtoBtn);});
    $(adicionaisBtn).on('click', function() {showSection('adicionais', adicionaisBtn, clienteBtn, medidasBtn, prod_servBtn, form_pgtoBtn);});
    $(form_pgtoBtn).on('click', function() {showSection('form_pgto', form_pgtoBtn, clienteBtn, medidasBtn, prod_servBtn, adicionaisBtn);});
    if ($('#medidas').length > 0) {showSection('medidas', medidasBtn, clienteBtn, prod_servBtn, adicionaisBtn, form_pgtoBtn);}
    if ($('#enderecos').length > 0) {showSection1('enderecos', endBt, compBt);}
    $('#id_serial, #id_nome_empresa, #id_nome_emp, #id_desc_prod').focus();
    // $('#loadingModal').modal({keyboard: true, backdrop: 'static'});
    // Chamadas AJAX SELECT2
    // Fornecedores
    $('#fornecedor, #id_forn, #id_fornecedor').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/fornecedores/lista_ajax/')}).on('select2:open', focSel2);
    // Vendedores
    $('#vendedor, #id_vend, #id_vendedor').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/vendedores/lista_ajax/')}).on('select2:open', focSel2);
    // Clientes
    $('#cliente, #id_cli, #id_cliente').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/clientes/lista_ajax/')}).on('select2:open', focSel2);
    // Cidades
    $('#id_cidade_fil, #id_cidade').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/cidades/lista_ajax/')}).on('select2:open', focSel2);
    // Estados
    $('#id_uf').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/estados/lista_ajax/')}).on('select2:open', focSel2);
    // Produtos
    $('#id_produto').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/produtos/lista_ajax1/')}).on('select2:open', focSel2);
    // Técnicos
    $('#id_solicitante, #tecnico, #id_tec').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/tecnicos/lista_ajax/')}).on('select2:open', focSel2);
    // Filiais
    $('#id_filial, #vinc_emp, #id_vinc_emp, [id^=filial_cr], #id_filial_user, #id_vinc_fil').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/filiais/lista_ajax/')}).on('select2:open', focSel2);
    // Empresas
    $('#emp, #id_empresa').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/empresas/lista_ajax/')}).on('select2:open', focSel2);
    // Regras de Produto
    $('#id_regra').select2({
        placeholder: opSel, allowClear: true, templateResult: renderRegra, templateSelection: d => d.text, language: lingSel, ajax: ajaxRegras('/regras_produto/lista_ajax/')}).on('select2:open', focSel2);~
    // Tabelas de Preço
    $('#tb-prec, #id_tabela_preco, #id_tb_preco, #id_tabela').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/tabelas_preco/lista_ajax/')}).on('select2:open', focSel2);
    // Só para o seletor da tabela ao realizar Entrada
    $('#id_tabelaEnt').select2({
        dropdownParent: $('#edProdModal'), placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/tabelas_preco/lista_ajax/')}).on('select2:open', focSel2);
    // Unidades
    $('#unidade, #unidade1, #campo-unidade-produto').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/unidades/lista_ajax/')}).on('select2:open', focSel2);
    // Para o modal Criação individual
    $('#xml-produto-unidade').select2({
        width:'100%',dropdownParent:$('#modalCriarProdutoXml'),placeholder:opSel,allowClear:true,templateResult:rendOpt,templateSelection:d=>d.text,language:lingSel,ajax:ajSel2('/unidades/lista_ajax/')}).on('select2:open', focSel2);
    $('#xml-produto-marca').select2({
        width: '100%', dropdownParent: $('#modalCriarProdutoXml'), placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel,ajax:ajSel2('/marcas/lista_ajax/')}).on('select2:open', focSel2);
    $('#xml-produto-grupo').select2({
        width: '100%', dropdownParent: $('#modalCriarProdutoXml'), placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel,ajax:ajSel2('/grupos/lista_ajax/')}).on('select2:open', focSel2);
    // Para o modal de criação em massa
    $('#massa-unidade').select2({
        width: '100%', dropdownParent: $('#modalCriarProdutoMassa'), placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel,ajax:ajSel2('/unidades/lista_ajax/')}).on('select2:open', focSel2);
    $('#massa-marca').select2({
        width: '100%', dropdownParent: $('#modalCriarProdutoMassa'), placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel,ajax:ajSel2('/marcas/lista_ajax/')}).on('select2:open', focSel2);
    $('#massa-grupo').select2({
        width: '100%', dropdownParent: $('#modalCriarProdutoMassa'), placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel,ajax:ajSel2('/grupos/lista_ajax/')}).on('select2:open', focSel2);
    // Bancos
    $('#id_banco_fil').select2({
        placeholder:'Selecione um banco', allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/bancos/lista_ajax/')}).on('select2:open', focSel2);
    // Formas de Pagamento
    $('#id_formas_pgto, #id_form_pgto, [id^="formas_pgto_cr"], [id^="formaPgtoSelect-"]').select2({
        placeholder:'Selecione uma forma', allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/formas_pgto/lista_ajax/')}).on('select2:open', focSel2);
    // Tipos de Cobrança
    $('#selTpCob').select2({
        placeholder:'Selecione um tipo', allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/tp_cobrancas/lista_ajax/')}).on('select2:open', focSel2);
    function createSelectWithAdd(config) {
        const {select,input,btnNew,btnOk,btnCancel,selectArea,inputArea,urlCreate,urlList,placeholder = 'Selecione...',entityName = 'Item'} = config;
        const $select      = $(select);
        const $input       = $(input);
        const $btnNew      = $(btnNew);
        const $btnOk       = $(btnOk);
        const $btnCancel   = $(btnCancel);
        const $selectArea  = $(selectArea);
        const $inputArea   = $(inputArea);
        const csrfToken    = $('input[name=csrfmiddlewaretoken]').val();
        // ===== SELECT2 =====
        function applySelect2($el) {
            if ($el.hasClass("select2-hidden-accessible")) {$el.select2('destroy');}
            $el.select2({width: '100%',placeholder,allowClear: true,templateResult: rendOpt,templateSelection: d => d.text,language: lingSel,ajax: ajSel2(urlList, entityName.toLowerCase() + 's')}).on('select2:open', focSel2);
        }
        // ===== UI =====
        function toggleUI(createMode) {
            $selectArea.toggle(!createMode);
            $inputArea.toggle(createMode);
            $btnNew.toggle(!createMode);
            $btnOk.toggle(createMode);
            $btnCancel.toggle(createMode);
            if (createMode) {setTimeout(() => $input.focus(), 100);}
        }
        // ===== CANCELAR =====
        function cancel() {
            $input.val('');
            toggleUI(false);
            applySelect2($select);
        }
        // ===== CRIAR =====
        function create() {
            const nome = $.trim($input.val());
            if (!nome) {
                toast(`${ic_amarelo} Digite o nome do ${entityName.toLowerCase()}!`, cor_amarelo);
                return $input.focus();
            }
            $btnOk.prop('disabled', true).html('<i class="fa fa-spinner fa-spin"></i>');
            $.ajax({url: urlCreate,type: 'POST',data: {nome,csrfmiddlewaretoken: csrfToken},
                success: function (data) {
                    cancel();
                    const option = new Option(data.nome, data.id, true, true);
                    $select.append(option).trigger('change');
                    setTimeout(() => {$select.trigger('change.select2');}, 150);
                    toast(`${ic_verde} ${entityName} criado com sucesso!`, cor_verde);
                },
                error: function () {
                    toast(`${ic_vermelho} Erro ao criar ${entityName.toLowerCase()}!`, cor_vermelho);
                    $btnOk.prop('disabled', false).html('<i class="fa fa-check"></i>');
                }
            });
        }
        // ===== UPPERCASE AUTOMÁTICO =====
        $input.on('input', function () {
            const pos = this.selectionStart;
            this.value = this.value.toUpperCase();
            this.setSelectionRange(pos, pos);
        });
        // ===== EVENTOS =====
        $btnNew.on('click', () => toggleUI(true));
        $btnCancel.on('click', cancel);
        $btnOk.on('click', create);
        $input.on('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                create();
            }
            if (e.key === 'Escape') {cancel();}
        });
        // ===== INIT =====
        applySelect2($select);
        // Retorna API (opcional, mas poderoso)
        return {refresh: () => applySelect2($select),openCreate: () => toggleUI(true),cancel};
    }
    // Grupos
    $('#grupo, #grupo1, #campo-grupo-produto').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/grupos/lista_ajax/')}).on('select2:open', focSel2);
    const grupoComponent = createSelectWithAdd({
        select: '#id_grupo',input: '#novo-grupo',btnNew: '#btn-novo-grupo',btnOk: '#btn-confirmar-grupo',btnCancel: '#btn-cancelar-grupo',selectArea: '#grupo-select-area',inputArea: '#grupo-input-area',
        urlCreate: '/grupos/add-ajax/',urlList: '/grupos/lista_ajax/',placeholder: 'Selecione um grupo',entityName: 'Grupo'
    });
    // Marcas
    $('#marca, #marca1, #campo-marca-produto').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/marcas/lista_ajax/')}).on('select2:open', focSel2);
    const marcaComponent = createSelectWithAdd({
        select: '#id_marca',input: '#nova-marca',btnNew: '#btn-nova-marca',btnOk: '#btn-confirmar-marca',btnCancel: '#btn-cancelar-marca',selectArea: '#marca-select-area',inputArea: '#marca-input-area',
        urlCreate: '/marcas/add-ajax/',urlList: '/marcas/lista_ajax/',placeholder: 'Selecione uma marca',entityName: 'Marca'
    });
    // Bairros
    const bairroComponent = createSelectWithAdd({
        select: '#id_bairro, #id_bairro_fil',input: '#novo-bairro',btnNew: '#btn-novo-bairro',btnOk: '#btn-confirmar-bairro',btnCancel: '#btn-cancelar-bairro',selectArea: '#bairro-select-area',inputArea: '#bairro-input-area',
        urlCreate: '/bairros/add-ajax/',urlList: '/bairros/lista_ajax/',placeholder: 'Selecione um bairro',entityName: 'Bairro'
    });
    // Unidades
    const unidadeComponent = createSelectWithAdd({
        select: '#id_unidProd',input: '#nova-unidade',btnNew: '#btn-nova-unidade',btnOk: '#btn-confirmar-unidade',btnCancel: '#btn-cancelar-unidade',selectArea: '#unidade-select-area',inputArea: '#unidade-input-area',
        urlCreate: '/unidades/add-ajax/',urlList: '/unidades/lista_ajax/',placeholder: 'Selecione uma unidade',entityName: 'Unidade'
    });
    // Selects unificados
    $('#id_unid_prod, #unid, #id_unidadeProduto, #id_form_pgto, #userSelect, #id_tp_chave, [id^="sel-status"]').select2({placeholder: 'Selecione uma opção', allowClear: true});
    // Funções referentes aos formulários de cadastro e edição
    $('#createForm').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.returnValue=false;
            e.cancel = true;
            e.stopPropagation();
        }
    });
    $('.formularios').on('keydown', function(e) {if (e.key === 'Enter') {e.preventDefault();}});
    function obterDataAtual2() {
        const dataAtual = new Date();
        const ano = dataAtual.getFullYear();
        let mes = (dataAtual.getMonth() + 1).toString().padStart(2, '0'); // Adiciona zero à esquerda, se necessário
        let dia = dataAtual.getDate().toString().padStart(2, '0'); // Adiciona zero à esquerda, se necessário
        return `${dia}/${mes}/${ano}`;}
    const seletorAutoData = '[id^="dt_pag_cr-"], #id_data_vencimento, .dt-fat-orcamento, .dt-fat-pedido, #id_dt_inicio, #id_dt_venc, #data, #id_dt_emi, #dt_efet_ent, #inpDtPriParc, #id_dt_ent, #id_data_aniversario, #id_data_emissao, #data_inicio1, #data_fim1, #id_data_doc, #id_data_prop, #id_dt_visita, #dtVisita, #id_dt_criacao';
    $(seletorAutoData).each(function () {if (!$(this).val()) {$(this).val(obterDataAtual2());}});
    if ($('#id_qtd, #id_quantidade').val() === '') {$('#id_qtd, #id_quantidade').val('1.00');}
    if ($('#id_rolo').val() === '') {$('#id_rolo').val('0.60');}
    if ($('#id_qtd_mens, #id_qtd_parcelas').val() === '') {$('#id_qtd_mens, #id_qtd_parcelas').val('1');}
    if ($('#id_valor, #id_juros, #id_multa, #id_vl_mens, #id_valor_mensalidade, #id_preco_unit, #id_vl_prod').val() === '') {$('#id_valor, #id_juros, #id_multa, #id_vl_mens, #id_valor_mensalidade, #id_preco_unit, #id_vl_prod').val('0.00');}
    const cepFormatado = (event) => {
        let input = event.target;
        input.value = cepMask(input.value);
    };
    const cepMask = (value) => {
        if (!value) return "";
        value = value.replace(/\D/g, '');
        value = value.replace(/^(\d{5})(\d)/, '$1-$2');
        return value;
    };
    $('#id_cep_administrador, #id_cep').on('input', function(event) {cepFormatado(event);});
    const dataFormatada = (event) => {
        let input = event.target;
        input.value = dataMask(input.value);
    };
    const dataMask = (value) => {
        if (!value) return "";
        value = value.replace(/\D/g, '');
        value = value.replace(/(\d{2})(\d)/, '$1/$2');
        value = value.replace(/(\d{2})(\d)/, '$1/$2');
        return value.substring(0, 10);
    };
    const seletorMascaraData = '[id^="dt_pag_cr-"], #id_data_vencimento, #id_dt_inicio, #data, .dt-fat-orcamento, .dt-fat-pedido, #id_dt_emi, #dt_efet_ent, #inpDtPriParc, #id_dt_ent, #id_dt_venc, #id_data_aniversario, #id_data_prop, #id_data_certificado, #id_data_nascimento, #id_data_nascimento_administrador, #data_inicio1, #data_fim1, #id_data_emissao, #id_data_entrega, #id_dt_criacao';
    $(document).on('input', seletorMascaraData, function (event) {dataFormatada(event);});
    const dataFormatada1 = (event) => {
        let input = event.target;
        input.value = dataMask1(input.value);
    };
    const dataMask1 = (value) => {
        if (!value) return "";
        value = value.replace(/\D/g, ''); // Remove todos os caracteres não numéricos
        value = value.replace(/(\d{2})(\d)/, '$1-$2'); // Insere o primeiro hifen
        value = value.replace(/(\d{2})(\d)/, '$1-$2'); // Insere o segundo hifen
        return value.substring(0, 10); // Limita o tamanho para 10 caracteres (dd-mm-aaaa)
    };
    $('#id_data_realizacao, #data_inicio, #data_fim').on('input', function(event) {dataFormatada1(event);});
    function normalizarNumero(valor) {
        if (valor === '' || valor === null || valor === undefined) {return '0.00';}
        let num = parseFloat(valor);
        if (isNaN(num)) {num = 0;}
        return num.toFixed(2);
    }
    let selectors = '#id_vl_form_pgto, #id_multi_m2, .inp-valor-pgto, #id_desc_acres, #id_preco_unitP, [id^=desc_m_cr], [id^=desc_j_cr], [id^=juros_cr], [id^=multa_cr], [id^=vl_pg_cr], .inp-valor, #id_valor, #id_juros, #id_multa, #id_vl_juros, #id_vl_multa, #id_ft_juros, #id_ft_multa, .valor-prod, .valor-prod-adc, .qtd-prod-adc, .qtd-prod, #campo_1, #campo_2, #id_margem, #id_vl_prod, #id_vl_tab, #id_vl_tabEnt, .inpFrete, #id_quantidade, #total-frete, .editable, #id_preco_unit, #id_valor_mensalidade, #id_vl_mens, #id_qtd, #id_m2, #id_acrescimo, #id_desconto, #id_vl_compra, #id_vl_compra_adc, #id_estoque_prod, #campo_desconto, #campo_acrescimo';
    $(selectors).each(function () {$(this).val(normalizarNumero($(this).val()));});
    $(document).on('input', selectors, function () {
        let valor = $(this).val();
        if (valor === '') {
            $(this).val('0.00');
            return;
        }
        let num = parseFloat(valor);
        if (isNaN(num)) {$(this).val('0.00');}
    });
    $(document).on('blur', selectors, function () {
        let num = parseFloat($(this).val());
        if (isNaN(num)) {num = 0;}
        $(this).val(num.toFixed(2));
    });
    function formatCurrency(input) {
        let value = input.value.replace(/\D/g, ''); // Remove todos os caracteres não numéricos
        let formattedValue = (parseFloat(value) / 100).toFixed(2).replace(',', '.').replace(/\B(?=(\d{3})+(?!\d))/g, ''); // Adiciona pontos como separadores de milhar
        input.value = formattedValue;
    }
    $(selectors).on('input', function(event) {formatCurrency(event.target);});
    $(selectors).on('focus', function(event) {
        let input = event.target;
        if (input.value === "0.00") {input.value = "0.00";}
    });
    const campoData = $('#id_data_aniversario');
    const campoDataAniversario = $('#id_id_data_aniversario');
    campoData.on('input', function () {campoDataAniversario.val(campoData.val());});
    const dataPesquisaInput = $("#data_pesquisa");
    const today = new Date().toISOString().slice(0, 10);
    dataPesquisaInput.val(today);
    // Listagem de Orçamentos no modal
    function formatMoneyBR(valor) {return parseFloat(valor || 0).toLocaleString('pt-BR', { minimumFractionDigits: 2 });}
    function montarTabelaItens(itens) {
        if (!itens || !itens.length) {return `<div class="text-center text-muted py-3">Nenhum item encontrado.</div>`;}
        let linhas = "";
        itens.forEach(function(item) {
            linhas += `
                <tr>
                    <td>${item.item}</td><td>${item.codigo}</td><td>${item.produto}</td><td>${item.unidade || ''}</td>
                    <td style="font-weight:bold;color:#2E8B57;">R$ ${formatMoneyBR(item.valor_unit)}</td><td>${item.qtd}</td><td style="font-weight:bold;color:#2E8B57;">R$ ${formatMoneyBR(item.valor_total)}</td>
                </tr>
            `;
        });
        return `
            <div class="table-responsive" style="max-height: 150px; overflow-y: auto;">
                <table class="table table-sm table-bordered table-responsive-sm table-rounded table-striped w-100 mb-0">
                    <thead class="table-dark">
                        <tr>
                            <th style="width: 1%;">Itens</th> <th style="width: 1%;">Código</th> <th style="width: 30%;">Descrição</th> <th style="width: 4%;">Unidade</th> <th style="width: 14%;">Vl. Unit.</th> <th style="width: 6%;">Qtde</th> <th>Vl. Total</th>
                        </tr>
                    </thead>
                    <tbody>${linhas}</tbody>
                </table>
            </div>
        `;
    }
    function montarAccordionPortas(portas, tipo, responseId) {
        if (!portas || !portas.length) {return `<div class="text-center text-muted py-3">Nenhuma porta encontrada.</div>`;}
        let html = `<div class="accordion" id="accordion_${tipo}_${responseId}">`;
        portas.forEach(function(porta, index) {
            const collapseId = `collapse_${tipo}_${responseId}_${porta.numero}`;
            const headingId = `heading_${tipo}_${responseId}_${porta.numero}`;
            const aberto = index === 0 ? 'show' : '';
            const collapsed = index === 0 ? '' : 'collapsed';
            const ariaExpanded = index === 0 ? 'true' : 'false';
            const titulo = tipo === 'produtos' ? `Produtos - Porta ${porta.numero}` : `Adicionais - Porta ${porta.numero}`;
            const itens = tipo === 'produtos' ? porta.produtos : porta.adicionais;
            html += `
                <div class="accordion-item mb-2">
                    <h2 class="accordion-header" id="${headingId}">
                        <button class="accordion-button ${collapsed} bg-body-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="${ariaExpanded}" aria-controls="${collapseId}" style="max-height: 30px;">
                            <strong>${titulo}</strong>
                        </button>
                    </h2>
                    <div id="${collapseId}" class="accordion-collapse collapse ${aberto}" aria-labelledby="${headingId}" data-bs-parent="#accordion_${tipo}_${responseId}">
                        <div class="accordion-body">${montarTabelaItens(itens)}</div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
        return html;
    }
    $(document).on('click', '#info-icon, .op-detalhe', function() {
        iniciarLoading();
        var idOrcamento = $(this).data('id');
        listarOrcamentos(idOrcamento);
        fecharLoading();
    });
    function listarOrcamentos(idOrcamento) {
        $.ajax({
            url: '/orcamentos/detalhes_ajax/' + idOrcamento + '/', type: 'GET',
            success: function(response) {
                $(`#infoEntModalLabel`).html('<strong><i class="fa-solid fa-circle-info text-white" style="float: none;"></i> Detalhes - Orçamento Nº ' + response.id + '</strong>');
                let situacaoTexto = response.situacao;
                let situacaoColor = "";
                let statusHTML = "";
                if (response.situacao === "Faturado") {
                    statusHTML = `
                        <div class="d-flex align-items-center gap-2 ms-2">
                            <label class="mb-0 fw-bold text-dark" for="sel-status-${response.id}">Status</label>
                            <select class="form-select form-select-sm text-dark" style="width:160px; background-color: #A9A9A9;" id="sel-status-${response.id}" name="sel-status-${response.id}" disabled>
                                <option value="Em Produção" ${response.status === "Em Produção" ? "selected" : ""}>Em Produção</option>
                                <option value="Embalada" ${response.status === "Embalada" ? "selected" : ""}>Embalada</option>
                                <option value="Instalada" ${response.status === "Instalada" ? "selected" : ""}>Instalada</option>
                                <option value="Entregue" ${response.status === "Entregue" ? "selected" : ""}>Entregue</option>
                            </select>
                            <i class="fa-solid fa-pen-to-square edit-status text-dark" style="cursor:pointer; font-size: 20px;" id="edit-status-${response.id}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="Alterar" data-id="${response.id}"></i>
                            <i class="fa-regular fa-circle-xmark text-dark" style="display:none;cursor:pointer; font-size: 20px;" id="cancel-status-${response.id}" data-bs-toggle="tooltip" data-bs-placement="top" data-bs-title="Cancelar" data-id="${response.id}"></i>
                        </div>
                    `;
                }
                if (response.situacao === "Aberto") {situacaoColor = "#005eff";}
                else if (response.situacao === "Faturado") {
                    situacaoColor = "#3CB371";
                    situacaoTexto = response.status;
                }
                else {situacaoColor = "#B22222";}
                const produtosAccordion = montarAccordionPortas(response.portas, 'produtos', response.id);
                const adicionaisAccordion = montarAccordionPortas(response.portas, 'adicionais', response.id);
                $(`#infoEntBody`).html(`
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label">Nº Orçamento</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.id}" disabled>
                        </div>
                        <div class="col-md-5">
                            <label class="form-label">Filial</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.cliente.empresa.nome}" disabled>
                        </div>
                        <div class="col-md-5">
                            <label class="form-label">Cliente</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.cliente.nome}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Solicitante</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.colaborador}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Data Emissão</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.data_emissao}" disabled>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Data Entrega</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.data_entrega}" disabled>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Valor Total</label>
                            <input class="form-control form-control-sm fw-bold" style="color:#2E8B57" value="R$ ${formatMoneyBR(response.vl_tot)}" disabled>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Situação</label>
                            <input class="form-control form-control-sm fw-bold" style="background:${situacaoColor};color:white;text-align:center" value="${situacaoTexto}" disabled>
                        </div>
                    </div>
                    <div class="col-12 mt-3">
                        <div class="card" style="margin: 0;">
                            <div class="card-header bg-secondary-subtle d-flex align-items-center gap-2 flex-wrap">
                                <button type="button" class="btn btn-dark btn-sm" id="medidasBtn${response.id}">Produtos</button>
                                <button type="button" class="btn btn-dark btn-sm" id="clienteBtn${response.id}">Adicionais</button>
                                ${statusHTML}
                            </div>
                            <div class="card-body">
                                <div class="form-section" id="medidas${response.id}">${produtosAccordion}</div>
                                <div class="form-section" id="clientes${response.id}" style="display:none;">${adicionaisAccordion}</div>
                            </div>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-md-12">
                            <label class="form-label">Observações</label>
                            <textarea class="form-control" disabled>${response.obs || ''}</textarea>
                        </div>
                    </div>
                `);
                document.querySelectorAll('#infoEntModal [data-bs-toggle="tooltip"]').forEach(function(el) {
                    const existingTooltip = bootstrap.Tooltip.getInstance(el);
                    if (existingTooltip) {existingTooltip.dispose();}
                    new bootstrap.Tooltip(el);
                });
                fecharLoading();
                $(`#infoEntModal`).modal('show');
            },
            error: function(xhr) {
                fecharLoading();
                console.error('Erro ao carregar orçamento:', xhr.responseText);
            }
        });
    }
    // Listagem de Pedidos no modal
    function montarTabelaItensPedido(itens) {
        if (!itens || !itens.length) {
            return `<div class="text-center text-muted py-3">Nenhum item encontrado.</div>`;
        }
        let linhas = "";
        itens.forEach(function(item) {
            const valor = parseFloat(item.desconto_acrescimo || 0);
            let sinal = '';

            if (valor !== 0) {
                sinal = item.tp_desc_acres === 'Desconto' ? '-' : '+';
            }

            linhas += `
                <tr>
                    <td>${item.item}</td>
                    <td>${item.codigo}</td>
                    <td>${item.produto}</td>
                    <td>${item.unidade || ''}</td>

                    <td style="font-weight:bold;color:#2E8B57;">
                        R$ ${formatMoneyBR(item.valor_unit)}
                    </td>

                    <td>${item.qtd}</td>

                    <td>
                        ${valor !== 0 ? `${sinal} R$ ${formatMoneyBR(valor)}` : ''}
                    </td>

                    <td style="font-weight:bold;color:#2E8B57;">
                        R$ ${formatMoneyBR(item.subtotal)}
                    </td>
                </tr>
            `;
        });
        return `
            <div class="table-responsive" style="max-height: 250px; overflow-y: auto;">
                <table class="table table-sm table-bordered table-striped w-100 mb-0">
                    <thead class="table-dark">
                        <tr>
                            <th>Item</th><th>Código</th><th>Descrição</th><th>Unidade</th><th>Vl. Unit.</th><th>Qtde</th><th>Desc/Acres</th><th>Subtotal</th>
                        </tr>
                    </thead>
                    <tbody>${linhas}</tbody>
                </table>
            </div>
        `;
    }
    $(document).on('click', '.op-detalhe-pedido', function() {
        iniciarLoading();
        const id = $(this).data('id');
        listarPedido(id);
    });
    function listarPedido(id) {
        $.ajax({
            url: '/pedidos/detalhes_ajax/' + id + '/', type: 'GET', success: function(response) {
                $('#infoEntModalLabel').html(
                    `<strong><i class="fa-solid fa-circle-info text-white"></i> Detalhes - Pedido Nº ${response.id}</strong>`
                );
                let situacaoColor = "#005eff";
                if (response.situacao === "Faturado") {
                    situacaoColor = "#3CB371";
                } else if (response.situacao === "Cancelado") {
                    situacaoColor = "#B22222";
                }
                const tabelaItens = montarTabelaItensPedido(response.itens);
                $('#infoEntBody').html(`
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label">Pedido</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.id}" disabled>
                        </div>
                        <div class="col-md-5">
                            <label class="form-label">Filial</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.filial}" disabled>
                        </div>
                        <div class="col-md-5">
                            <label class="form-label">Cliente</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.cliente}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Vendedor</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.vendedor}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Data Emissão</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.data_emissao}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Total</label>
                            <input class="form-control form-control-sm fw-bold" style="color:#2E8B57" value="R$ ${formatMoneyBR(response.total)}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Situação</label>
                            <input class="form-control form-control-sm fw-bold" style="background:${situacaoColor};color:white;text-align:center" value="${response.situacao}" disabled>
                        </div>
                    </div>
                    <div class="col-12 mt-3">
                        <div class="card">
                            <div class="card-header bg-secondary-subtle text-dark">
                                <strong>Itens do Pedido</strong>
                            </div>
                            <div class="card-body">
                                ${tabelaItens}
                            </div>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-md-12">
                            <label class="form-label">Observações</label>
                            <textarea class="form-control" disabled>${response.obs || ''}</textarea>
                        </div>
                    </div>
                `);
                fecharLoading();
                $('#infoEntModal').modal('show');
            },
            error: function(xhr) {
                fecharLoading();
                console.error('Erro ao carregar pedido:', xhr.responseText);
            }
        });
    }
    // Lista para Contas A Receber
    function montarTabelaFormasCR(formas) {
        if (!formas || !formas.length) {
            return `<div class="text-center text-muted py-3">Nenhuma baixa registrada.</div>`;
        }

        let linhas = "";

        formas.forEach(f => {
            linhas += `
                <tr>
                    <td>${f.item}</td>
                    <td>${f.forma}</td>
                    <td class="text-end fw-bold text-success">
                        R$ ${formatMoneyBR(f.valor)}
                    </td>
                </tr>
            `;
        });

        return `
            <div class="table-responsive" style="max-height: 200px;">
                <table class="table table-sm table-bordered table-striped mb-0">
                    <thead class="table-dark">
                        <tr>
                            <th>#</th>
                            <th>Forma</th>
                            <th>Valor</th>
                        </tr>
                    </thead>
                    <tbody>${linhas}</tbody>
                </table>
            </div>
        `;
    }
    $(document).on('click', '.op-detalhe-cr', function() {
        iniciarLoading();
        const id = $(this).data('id');
        listarContaReceber(id);
    });
    function listarContaReceber(id) {
        $.ajax({
            url: '/contas_receber/detalhes_ajax/' + id + '/',
            type: 'GET',

            success: function(response) {

                let cor = "#005eff";

                if (response.situacao === "Paga") {
                    cor = "#3CB371";
                } else if (response.vencido) {
                    cor = "#B22222";
                }

                const tabelaFormas = montarTabelaFormasCR(response.formas);

                $('#infoEntModalLabel').html(
                    `<strong><i class="fa-solid fa-file-invoice-dollar text-white"></i> Conta Nº ${response.num_conta}</strong>`
                );

                $('#infoEntBody').html(`
                    <div class="row g-3">

                        <div class="col-md-2">
                            <label>Nº Conta</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.num_conta}" disabled>
                        </div>

                        <div class="col-md-5">
                            <label>Filial</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.filial}" disabled>
                        </div>

                        <div class="col-md-5">
                            <label>Cliente</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.cliente}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Emissão</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.data_emissao}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Vencimento</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.data_vencimento}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Pagamento</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.data_pagamento || '-'}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Situação</label>
                            <input class="form-control form-control-sm fw-bold text-center"
                                style="background:${cor};color:white"
                                value="${response.situacao}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Valor</label>
                            <input class="form-control form-control-sm fw-bold text-success"
                                value="R$ ${formatMoneyBR(response.valor)}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Juros</label>
                            <input class="form-control form-control-sm"
                                value="R$ ${formatMoneyBR(response.juros)}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Multa</label>
                            <input class="form-control form-control-sm"
                                value="R$ ${formatMoneyBR(response.multa)}" disabled>
                        </div>

                        <div class="col-md-3">
                            <label>Desconto</label>
                            <input class="form-control form-control-sm text-danger"
                                value="R$ ${formatMoneyBR(response.desconto)}" disabled>
                        </div>
                    </div>

                    <div class="col-12 mt-3">
                        <div class="card">
                            <div class="card-header bg-secondary-subtle text-dark">
                                <strong>Formas de Pagamento</strong>
                            </div>
                            <div class="card-body">
                                ${tabelaFormas}
                            </div>
                        </div>
                    </div>

                    <div class="mt-3">
                        <label>Observações</label>
                        <textarea class="form-control" disabled>${response.obs}</textarea>
                    </div>
                    <div class="mt-3">
                        <label>Observações Internas</label>
                        <textarea class="form-control" disabled>${response.obs_internas}</textarea>
                    </div>
                `);

                fecharLoading();
                $('#infoEntModal').modal('show');
            },

            error: function(xhr) {
                fecharLoading();
                console.error('Erro:', xhr.responseText);
            }
        });
    }
});