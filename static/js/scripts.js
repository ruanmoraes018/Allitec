$(document).ready(function() {
    const prodManager = {
        data: {},
        currentEditing: {
            porta: null,
            itemId: null,
            $tr: null
        },

        ensurePorta(porta) {
            if (!this.data[porta]) this.data[porta] = [];
        },

        setEditingItem($tr) {
            this.currentEditing = {
                porta: Number($tr.data('porta')),
                itemId: Number($tr.data('item-id')),
                $tr
            };
        },

        addItem(porta, item) {
            this.ensurePorta(porta);

            item.id = Date.now(); // 🔥 ID único
            item.qtd_manual = false;

            this.data[porta].push(item);
            return item.id;
        },
        updateEditingItem(cells) {
            console.log('CELLS RECEBIDO:', cells);
            const { porta, itemId, $tr } = this.currentEditing;
            const portaKey = Number(porta);

            const item = this.data[portaKey]?.find(i => i.id === itemId);
            if (!item) return;

            const novoCod  = cells[0];
            const novaDesc = cells[1];
            const novaUnid = cells[2];
            const novoVl   = parseFloat(cells[3]) || 0;
            const novaQtd  = parseFloat(cells[4]);

            const mudou =
                item.cod     !== novoCod ||
                item.desc    !== novaDesc ||
                item.unid    !== novaUnid ||
                item.vl_unit !== novoVl  ||
                (
                    !isNaN(novaQtd) &&
                    Number(item.qtd_final ?? 0) !== novaQtd
                );

            if (!mudou) {
                console.log('Nenhuma alteração detectada');
                return;
            }

            /* ================== DATA (fonte da verdade) ================== */
            item.cod     = novoCod;
            item.desc    = novaDesc;
            item.unid    = novaUnid;
            item.vl_unit = novoVl;

            if (!isNaN(novaQtd)) {
                item.qtd_final  = novaQtd;
                item.qtd_manual = true;
                item.ativo      = novaQtd > 0;
            }

            /* ================== DOM ================== */
            $tr.find('.td-cod').text(item.cod);
            $tr.find('.td-desc').text(item.desc);
            $tr.find('.td-unid').text(item.unid);
            $tr.find('.vl-unit').text(item.vl_unit.toFixed(2));
            $tr.find('.qtd-produto').text(item.qtd_final.toFixed(2));

            /* ================== RECÁLCULO CORRETO ================== */
            atualizarTabelaPorta(porta); // ✅ AGORA SIM
            atualizarSubtotal();
            atualizarJSONPortas();
        },
        removeItemById(porta, itemId) {
            if (!this.data[porta]) return;

            this.data[porta] = this.data[porta].filter(i => i.id !== itemId);
        },

        resetPorta(porta) {
            this.data[porta] = [];
        },

        clearEditing() {
            this.currentEditing = { porta: null, itemId: null, $tr: null };
        }
    };
    const prodAdcManager = {
        data: {},
        currentEditing: {
            porta: null,
            itemId: null,
            $tr: null
        },

        ensurePorta(porta) {
            if (!this.data[porta]) this.data[porta] = [];
        },

        setEditingItem($tr) {
            this.currentEditing = {
                porta: Number($tr.data('porta')),
                itemId: Number($tr.data('item-id')),
                $tr
            };
        },

        addItem(porta, item) {
            this.ensurePorta(porta);

            item.id = Date.now();
            item.qtd_manual = false;

            this.data[porta].push(item);
            return item.id;
        },
        updateEditingItem(cells) {
            console.log('CELLS RECEBIDO:', cells);
            const { porta, itemId, $tr } = this.currentEditing;
            const portaKey = Number(porta);

            const item = this.data[portaKey]?.find(i => i.id === itemId);
            if (!item) return;

            // 🔹 Valores novos
            const novoCod  = cells[0];
            const novaDesc = cells[1];
            const novaUnid = cells[2];
            const novoVl   = parseFloat(cells[3]) || 0;
            const novaQtd  = parseFloat(cells[4]);

            // 🔎 Verifica mudanças reais
            const mudou =
                item.cod      !== novoCod ||
                item.desc     !== novaDesc ||
                item.unid     !== novaUnid ||
                item.vl_unit  !== novoVl  ||
                (
                    !isNaN(novaQtd) &&
                    Number(item.qtd_final ?? 0) !== novaQtd
                );

            if (!mudou) {
                console.log('Nenhuma alteração detectada');
                return;
            }

            /* ================== DATA (fonte da verdade) ================== */
            item.cod     = novoCod;
            item.desc    = novaDesc;
            item.unid    = novaUnid;
            item.vl_unit = novoVl;

            if (!isNaN(novaQtd)) {
                item.qtd_final  = novaQtd;
                item.qtd_manual = true;          // 🔒 REGRA DE OURO
                item.ativo      = novaQtd > 0;
            }

            /* ================== DOM ================== */
            $tr.find('.td-cod').text(item.cod);
            $tr.find('.td-desc').text(item.desc);
            $tr.find('.td-unid').text(item.unid);
            $tr.find('.vl-unit').text(item.vl_unit.toFixed(2));
            $tr.find('.qtd-produto').text(item.qtd_final.toFixed(2));

            /* ================== RECÁLCULO SEGURO ================== */
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            atualizarJSONPortas();
        },
        removeItemById(porta, itemId) {
            if (!this.data[porta]) return;

            this.data[porta] = this.data[porta].filter(i => i.id !== itemId);
        },

        resetPorta(porta) {
            this.data[porta] = [];
        },

        clearEditing() {
            this.currentEditing = { porta: null, itemId: null, $tr: null };
        }
    };
    console.log(prodManager.data[0]);
    console.log(prodAdcManager.data[0]);
    
    function getPortasFromBackend() {
        const el = document.getElementById('json-portas');
        if (!el) return [];

        let raw = el.textContent || el.innerText || '';

        raw = raw.trim();

        if (!raw) return [];

        try {
            const parsed = JSON.parse(raw);

            // 🔒 GARANTIA ABSOLUTA
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

    hidratarManagersFromBackend();

    var form = $('#createForm');
    var cadastro = 'https://allitec.pythonanywhere.com/orcamentos/add/';
    calcTotalEntrada();
    $('.table').addClass("table-sm");
    $('[name^="nome_"]').first().focus();
    $('[name^="descricao"]').first().focus();
    // Função do Toastify
    let cor_verde = "linear-gradient(to right, #00b09b, #96c93d)";
    let cor_vermelho = "linear-gradient(to right, #ff416c, #ff4b2b)";
    let cor_amarelo = "linear-gradient(to right, #ff9f00, #ff6f00)";
    let cor_info = "linear-gradient(to right, #02202B, #017AB1)";
    let cor_padrao = "linear-gradient(to right, #333, #555)";
    function toast(msg, cor="#333") {
        Toastify({
            text: msg,
            duration: 5000,
            gravity: "top",
            position: "center",
            backgroundColor: cor,
            stopOnFocus: true,
            escapeMarkup: false,
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

    // Habilitar campo de portão social
    $('#id_portao_social').on('change', function () {
        const p_social = $(this).val();
        if (p_social === 'Não') {
            $("#id_vl_p_s").val('0');
            $("#id_vl_p_s").prop("disabled", true);
            atualizarSubtotal();
        } else if (p_social === "Sim") {
            $("#id_vl_p_s").prop("disabled", false);
        }
    });
    $("#id_vl_p_s").on("blur", function() {
        atualizarSubtotal();
    });
    // Mudança no status de Orçamento Faturado
    $('[id^="sel-status"]').select2({
        placeholder: 'Selecione uma opção',
        allowClear: true
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    // Clicar no EDIT
    $(document).on("click", ".edit-status", function () {
        const id = $(this).data("id");
        const $select = $(`#sel-status-${id}`);
        const $cancel = $(`#cancel-status-${id}`);
        if ($select.prop("disabled")) {
            $select.prop("disabled", false);
            $cancel.show();
            return; // primeira etapa concluída
        }
        const novoStatus = $select.find("option:selected").text();
        $(`#novoStatusTexto${id}`).text(novoStatus);
        const modal = new bootstrap.Modal(
            document.getElementById(`modalConfirmacaoStatus${id}`)
        );
        modal.show();
    });
    // Clicar no CANCELAR
    $(document).on("click", ".fa-circle-xmark", function () {
        const id = $(this).data("id");
        const $select = $(`#sel-status-${id}`);
        $select.prop("disabled", true);
        $(this).hide(); // esconder cancelar
    });
    // CONFIRMAR no modal
    $(document).on("click", ".confirm-status", function () {
        const modalElement = $(this).closest(".modal").attr("id");
        const id = modalElement.replace("modalConfirmacaoStatus", "");
        const $select = $(`#sel-status-${id}`);
        const novoStatus = $select.val();
        $.ajax({
            url: "/orcamentos/alterar-status/",
            method: "POST",
            data: {
                id: id,
                status: novoStatus,
                csrfmiddlewaretoken: $("input[name=csrfmiddlewaretoken]").val(),
            },
            success: function () {
                toast("<i class='fa-solid fa-circle-check'></i> Status atualizado com sucesso!", cor_verde);
                $select.prop("disabled", true);
                $(`#cancel-status-${id}`).hide();
                const bsModal = bootstrap.Modal.getInstance(
                    document.getElementById(`modalConfirmacaoStatus${id}`)
                );
                const resumoModal = bootstrap.Modal.getInstance(
                    document.getElementById(`infoEntModal${id}`)
                );
                bsModal.hide();
                resumoModal.hide();
                setTimeout(function () {
                    $("#data-btn").click();
                    finalizarLoading();
                }, 1500);
            },
            error: function () {
                toast("<i class='fa-solid fa-circle-xmark'></i> Erro ao atualizar o status!", cor_vermelho);
            }
        });
    });
    $(function () {
        $('[data-bs-toggle="tooltip"]').each(function () {
            new bootstrap.Tooltip(this);
        });
    });
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
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Selecione ao menos um produto antes de continuar!", cor_amarelo);
            return;
        }
        $('#attTbPrecModal').modal('show');
    });
    // VISUALIZAR ENTRADAS DE PRODUTO
    $('.ver-entradas').on('click', function() {
        const produtoId = $(this).data('produto-id');
        const modalEl = $(`#infoEntModal${produtoId}`)[0];
        const modal = new bootstrap.Modal(modalEl);
        const tableBody = $(`#entradasTableBody${produtoId}`);
        $.ajax({
            url: `/entradas/entradas-produto/${produtoId}/`,
            method: 'GET',
            dataType: 'json',
            success: function(response) {
                tableBody.empty(); // limpa o corpo da tabela
                if (response.entradas.length > 0) {
                    $.each(response.entradas, function(i, e) {
                        const row = `
                            <tr>
                                <td>${e.fornecedor}</td>
                                <td>${e.data}</td>
                                <td>${e.entrada_id}</td>
                                <td>${e.quantidade}</td>
                                <td>R$ ${e.valor_unitario.toFixed(2).replace('.', ',')}</td>
                                <td><strong>R$ ${e.total_entrada.toFixed(2).replace('.', ',')}</strong></td>
                            </tr>
                        `;
                        tableBody.append(row);
                    });
                } else {
                    tableBody.append('<tr><td colspan="6" class="text-center">Nenhuma entrada encontrada.</td></tr>');
                }
                modal.show();
            },
            error: function() {
                tableBody.html('<tr><td colspan="6" class="text-center text-danger">Erro ao carregar dados.</td></tr>');
                modal.show();
            }
        });
    });
    // NOVO TESTE
    $( function() {
      $("#dt_efet_ent, #inpDtPriParc, #id_dt_inicio, #data, #id_dt_emi, #id_dt_ent, #id_dt_venc, #id_data_certificado, #id_data_emissao, #id_data_emissao1, #id_data_entrega, #data_inicio1, #data_fim1, #id_data_nascimento_administrador, #id_data_nascimento, #id_data_doc, #id_data_prop, #id_data_aniversario, #id_dt_visita, #id_px_visita, #dtVisita, #pxVisita, #id_dt_criacao").datepicker({
        changeMonth: true,
        changeYear: true,
        dateFormat: "dd/mm/yy",
        monthNamesShort: [ "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez" ],
        dayNamesMin: [ "Do", "2ª", "3ª", "4ª", "5ª", "6ª", "Sá" ]});
    });
    // Usado quando o modal FaturarModal é aberto
    $(document).on('shown.bs.modal', '[id^="faturarModal-"]', function () {
        const inpParc = $(this).find('#inpParc');
        const inpDiasPriParc = $(this).find('#inpDiasPriParc');
        const inpIntervalo = $(this).find('#inpIntervalo');
        const dtEfetivacao = $(this).find('#dt_efet_ent');
        const inpDtPriParc = $(this).find('#inpDtPriParc');
        // Valores default
        if (!inpParc.val()) {
            inpParc.val(1);
        }
        if (!inpDiasPriParc.val()) {
            inpDiasPriParc.val(1);
        }
        if (!inpIntervalo.val()) {
            inpIntervalo.val(0);
        }
        if (!dtEfetivacao.val()) {
            dtEfetivacao.val(obterDataAtual2()); // função sua para pegar a data atual
        }
        if (dtEfetivacao.val()) {
            inpDtPriParc.val(addDtInterv(dtEfetivacao.val(), inpDiasPriParc.val()));
        }
        $('#dt_efet_ent, #inpDiasPriParc').on('change', function () {
            const dtEfetiv = $('#dt_efet_ent').val();
            const interv = $('#inpDiasPriParc').val();
            if (dtEfetiv && interv) {
                const nvDtPriParc = addDtInterv(dtEfetiv, interv);
                $('#inpDtPriParc').val(nvDtPriParc);
            }
        });
    });
    // Bloqueia o flatpickr de abrir quando o evento vem de dentro do Select2
    $(document).on("focusin", function(e) {
        if ($(e.target).closest(".select2-container").length) {
            e.stopImmediatePropagation();
        }
    });
    // Função para Entrada de NF e Pedidos
    $('#id_desconto').on("blur", function() {
        let valor = $(this).val().replace(',', '.').trim();
        if (valor === "" || isNaN(valor)) {
            $(this).val("0.00");
        } else {
            $(this).val(parseFloat(valor).toFixed(2));
        }
    });
    $(document).on("click", ".editable#total-frete", function () {
        const $span = $(this);
        const valor = $span.text().trim();
        const $input = $(`<input type="text" id="total-frete" class="form-control d-inline-block w-auto inpFrete" value="${valor}">`);
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
                    <span class="editable" id="total-frete"
                          style="background-color: #F08080; color: white; border-radius: 15px; padding-left: 10px; padding-right: 10px; float: right;">
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
            let vlProdTxt = $(this).find('td:nth-child(6)').text().trim().replace(',', '.');
            let vlProdNb = parseFloat(vlProdTxt);
            if (!isNaN(vlProdNb)) {
                produtos += vlProdNb;
            }
            let vlDsctTxt = $(this).find('td:nth-child(5)').text().trim().replace(',', '.');
            let vlDsctNb = parseFloat(vlDsctTxt);
            if (!isNaN(vlDsctNb)) {
                desconto += vlDsctNb;
            }
        });
        let freteTxt = $('#total-frete').is('input')
            ? $('#total-frete').val()
            : $('#total-frete').text();
        frete = parseFloat(freteTxt.replace(',', '.')) || 0;
        total = produtos + frete;
        $('#total-produtos').text('R$ ' + produtos.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#total-desconto').text('R$ ' + desconto.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#total-frete').text(frete.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        $('#id_frete').val(
            Number(frete).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        );
        $('#valor-total').text('R$ ' + total.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
    }
    // Entrada de Pedidos
    $('#id_tipo').on('change', function () {
        const tipoEnt = $(this).val();
        if (tipoEnt === 'Pedido') {
            $("#id_modelo, #id_serie, #id_nat_op, #id_chave_acesso").prop("disabled", true);
        } else if (tipoEnt === "Nota Fiscal") {
            $("#id_modelo, #id_serie, #id_nat_op, #id_chave_acesso").prop("disabled", false);
        }
    });
    // Add código secundário nos Produtos
    let ident = 0;
    // Adicionando um produto na lista.
    $("#add-cod-sec-tab").click(function () {
        let cod = $('#cod-sec').val();
        if (cod === "") {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Código deve ser informado!", cor_amarelo);
        } else {
            // === Criar nova linha ===
            let idx = ident++;
            let codigoJaExiste = false;
            $("#tb-cod-sec tbody input[name*='[codigo]']").each(function() {
                if ($(this).val() === cod) {
                    codigoJaExiste = true;
                    return false; // sai do each
                }
            });
            if (codigoJaExiste) {
                toast(`<i class="fa-solid fa-triangle-exclamation"></i> O código "${cod}" já está incluso na listagem!`, cor_amarelo);
            } else {
                // Só adiciona se não existir
                $("#tb-cod-sec tbody").append(`
                    <tr data-id="${idx}">
                        <td>${cod}<input type="hidden" name="codigo[${idx}][codigo]" value="${cod}"></td>
                        <td>
                            <button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>
                `);
            }
        }
        $("#cod-sec").val("");
        $("#cod-sec").focus();
    });
    // excluir linha
    $(document).on("click", ".remover", function () {
        $(this).closest("tr").remove();
    });
    $('#cod-sec').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault(); // evita o submit do form
            $("#add-cod-sec-tab").click(); // aciona o mesmo evento do botão
        }
    });
    // Pra Adicionar Tabela de Preço de Produto
    let trEdit = null;          // variável global para edição
    let identificador = $("#tab-prec tbody tr").length; // contador inicial
    let editing = false;        // flag para evitar sobrescrever margem ao editar
    let bloqueio = false;       // evita loop de eventos
    // ======= REACALCULOS AUTOMÁTICOS =======
    $('#id_vl_prod').on('blur', function () {
        if (bloqueio) return;
        bloqueio = true;
        const valorCompra = parseFloat($('#id_vl_compra').val()) || 0;
        const valorProduto = parseFloat($(this).val()) || 0;
        if (valorCompra > 0 && valorProduto > 0) {
            const margem = ((valorProduto - valorCompra) / valorCompra) * 100;
            $('#id_margem').val(margem < 0 ? '0.00' : margem.toFixed(2));
        } else {
            $('#id_margem').val('0.00');
        }
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
            $('#id_vl_prod').val(valorProduto.toFixed(2));
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
            $('#id_vl_prod').val(valorProduto.toFixed(2));
        }
        bloqueio = false;
    });
    // ======= CHANGE DA TABELA =======
    $('#id_tabela').on('change', function () {
        if (editing) return; // ignora quando estiver editando
        const tp_atrib = $('#tp-atrib').val();
        const tabelaId = $(this).val();
        const precoCompra = parseFloat($('#id_vl_compra').val()) || 0;
        if (!tabelaId) return;
        $.ajax({
            url: "/tabelas_preco/get/",
            method: "GET",
            data: { id: tabelaId },
            success: function(response) {
                if (response.margem !== undefined) {
                    $('#id_margem').val(response.margem);
                    if (tp_atrib === "0") {
                        $('#campo_1').val(response.margem);
                    }
                    let calc = precoCompra * (1 + response.margem / 100);
                    $('#id_vl_prod').val(calc.toFixed(2));
                }
            },
            error: function() {
                toast("<i class='fa-solid fa-circle-xmark'></i> Erro ao buscar a tabela de preço!", cor_vermelho);
            }
        });
    });
    $('#tb-prec').on('change', function () {
        if (editing) return; // ignora quando estiver editando
        const tp_atrib = $('#tp-atrib').val();
        const tabelaId = $(this).val();
        const precoCompra = parseFloat($('#id_vl_compra').val()) || 0;
        if (!tabelaId) return;
        $.ajax({
            url: "/tabelas_preco/get/",
            method: "GET",
            data: { id: tabelaId },
            success: function(response) {
                if (response.margem !== undefined) {
                    if (tp_atrib === "0") {
                        $('#campo_1').val(response.margem);
                    }
                    let calc = precoCompra * (1 + response.margem / 100);
                    $('#id_vl_prod').val(calc.toFixed(2));
                }
            },
            error: function() {
                toast("<i class='fa-solid fa-circle-xmark'></i> Erro ao buscar a tabela de preço!", cor_vermelho);
            }
        });
    });
    // ======= ADD / EDIT / REMOVE =======
    $('#add-tab').css('background-color', '').html('<i class="fa-solid fa-plus"></i> Incluir');
    // Função para resetar inputs
    function resetInputs() {
        $("#id_vl_prod, #id_margem").val("0.00");
        $('#id_tabela').val(null).trigger('change');
        $("#id_tabela").focus();
    }
    // Clique no botão para adicionar ou salvar
    $("#add-tab").click(function () {
        let tabId = $('#id_tabela').val();
        let tabNome = $('#id_tabela option:selected').text();
        let mrg = $("#id_margem").val();
        let vl_p = $("#id_vl_prod").val();
        if (!tabId) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Selecione uma tabela antes de adicionar!", cor_amarelo);
            return;
        }
        if (vl_p === "0.00" || vl_p === "" || vl_p === "0") {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Preço de Venda deve ser informado!", cor_amarelo);
            return;
        }
        if (trEdit) {
            let idx = trEdit.data("id");
            trEdit.find("td:eq(0)").html(`${tabNome}<input type="hidden" name="tab_preco[${idx}][tabela]" value="${tabId}">`);
            trEdit.find("td:eq(1)").html(`${mrg}<input type="hidden" name="tab_preco[${idx}][margem]" value="${mrg}">`);
            trEdit.find("td:eq(2)").html(`${vl_p}<input type="hidden" name="tab_preco[${idx}][vl_prod]" value="${vl_p}">`);
            trEdit = null;
            $("#id_tabela").prop("disabled", false);
            $('#add-tab')
                .css('background-color', '')
                .html('<i class="fa-solid fa-plus"></i> Incluir');
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
            if (tabelaJaExiste) {
                toast(`Tabela "${tabNome}" já está inclusa na listagem!`, cor_amarelo);
            } else {
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
        resetInputs();
    });
    // ======= REMOVER LINHA =======
    $(document).on("click", ".remover", function () {
        $(this).closest("tr").remove();
    });
    // ======= EDITAR LINHA =======
    $(document).on("click", ".editando", function () {
        trEdit = $(this).closest("tr");
        const idx = trEdit.data("id");
        const tabId = trEdit.find(`input[name="tab_preco[${idx}][tabela]"]`).val();
        const mrg = trEdit.find(`input[name="tab_preco[${idx}][margem]"]`).val();
        const vl_p = trEdit.find(`input[name="tab_preco[${idx}][vl_prod]"]`).val();
        editing = true; // ativa flag para ignorar change da tabela
        const select = $("#id_tabela");
        if (select.find(`option[value='${tabId}']`).length === 0) {
            const tabText = trEdit.find("td:eq(0)").text().trim();
            select.append(`<option value="${tabId}">${tabText}</option>`);
        }
        select.val(tabId).trigger('change');
        select.prop("disabled", true);
        // Setar campos com os valores já salvos
        $("#id_margem").val(mrg);
        $("#id_vl_prod").val(vl_p);
        $("#id_vl_prod").focus();
        // Muda botão para "Salvar"
        $('#add-tab')
            .css('background-color', 'gray')
            .html('<i class="fa-solid fa-floppy-disk"></i> Salvar');
        editing = false; // desativa flag após setar
    });
    //
    let contador = 0;
    let trEditando = null; // linha que está em edição
    let unidadeTmp = "";
    let grupoTmp = "";
    // Adicionando um produto na lista.
    $("#add-produto-lista").click(function () {
        let cod = $('#id_cod_produto').val(),
            prod = $("#id_desc_prod").val(),
            qtd = $("#id_quantidade").val(),
            preco = $("#id_preco_unit").val(),
            dsct = $("#id_desconto").val(),
            total = ((preco * qtd) - dsct).toFixed(2);
        if ($("#id_preco_unit").val() === "0.00") {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Preço Unitário deve ser informado!", cor_amarelo);
        } else if (trEditando) {
            // === Atualizar linha existente ===
            let idx = trEditando.data("id");
            trEditando.find("td:eq(0)").html(`${cod} <input type="hidden" name="produtos[${idx}][codigo]" value="${cod}">`);
            trEditando.find("td:eq(1)").html(`${prod} <input type="hidden" name="produtos[${idx}][produto]" value="${prod}">`);
            trEditando.find("td:eq(2)").html(`${qtd} <input type="hidden" name="produtos[${idx}][quantidade]" value="${qtd}">`);
            trEditando.find("td:eq(3)").html(`${preco} <input type="hidden" name="produtos[${idx}][preco_unitario]" value="${preco}">`);
            trEditando.find("td:eq(4)").html(`${dsct} <input type="hidden" name="produtos[${idx}][desconto]" value="${dsct}">`);
            trEditando.find("td:eq(5)").text(total);
            trEditando = null; // sai do modo edição
            calcTotalEntrada();
            $('#edProdModal').modal('hide');
        } else {
            // === Criar nova linha ===
            let idx = contador++;
            $("#tabela-produtos tbody tr.vazio").remove();
            // Supondo que `cod` seja o código do produto que o usuário está tentando inserir
            let codigoJaExiste = false;
            // Verifica se já existe um <input hidden> com esse código dentro da tabela
            $("#tabela-produtos tbody input[name*='[codigo]']").each(function() {
                if ($(this).val() === cod) {
                    codigoJaExiste = true;
                    return false; // sai do each
                }
            });
            if (codigoJaExiste) {
                toast(`<i class="fa-solid fa-triangle-exclamation"></i> O código "${cod}" já está incluso na listagem!`, cor_amarelo);
            } else {
                // Só adiciona se não existir
                $("#tabela-produtos tbody").append(`
                    <tr data-id="${idx}">
                        <td>${cod}<input type="hidden" name="produtos[${idx}][codigo]" value="${cod}"></td>
                        <td>${prod}<input type="hidden" name="produtos[${idx}][produto]" value="${prod}"></td>
                        <td>${qtd}<input type="hidden" name="produtos[${idx}][quantidade]" value="${qtd}"></td>
                        <td style="font-weight: bold; color: #2E8B57;">${preco}<input type="hidden" name="produtos[${idx}][preco_unitario]" value="${preco}"></td>
                        <td>${dsct}<input type="hidden" name="produtos[${idx}][desconto]" value="${dsct}"></td>
                        <td style="font-weight: bold; color: #2E8B57;">${total}</td>
                        <td>
                            <button type="button" class="editar btn btn-success btn-sm mt-1 mb-1"><i class="fa-solid fa-pen-to-square"></i></button>
                            <button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>
                `);
                calcTotalEntrada();
            }
        }
        unidadeTmp = $("#id_unidProduto").val();
        grupoTmp = $("#id_grupoProd").val();
        // limpa inputs
        $("#id_desc_prod, #id_unidProd, #id_grupoProd, #id_cod_produto").val("");
        $("#id_quantidade").val("1.00");
        $("#id_preco_unit").val("0.00");
        $("#id_desconto").val("0.00");
        $("#id_cod_produto").focus();
    });
    $("#cancelar-produto-lista").click(function () {
        trEditando = null;
        // limpa inputs
        $("#id_desc_prod, #id_unidProduto, #id_grupoProd, #id_cod_produto").val("");
        $("#id_quantidade").val("1.00");
        $("#id_preco_unit").val("0.00");
        $("#id_desconto").val("0.00");
        $("#id_cod_produto").prop("disabled", false);
        $("#add-prod").prop("readonly", false);
    });
    // excluir linha
    $(document).on("click", ".remover", function () {
        $(this).closest("tr").remove();
        calcTotalEntrada();
    });
    // editar linha
    $(document).on("click", ".editar", function () {
        trEditando = $(this).closest("tr"); // guarda a linha atual
        let idx = trEditando.data("id");
        // pega valores dos hidden
        let cod = trEditando.find(`input[name="produtos[${idx}][codigo]"]`).val();
        let prod = trEditando.find(`input[name="produtos[${idx}][produto]"]`).val();
        let qtd = trEditando.find(`input[name="produtos[${idx}][quantidade]"]`).val().replace(',', '.');
        let preco = trEditando.find(`input[name="produtos[${idx}][preco_unitario]"]`).val().replace(',', '.');
        let dsct = trEditando.find(`input[name="produtos[${idx}][desconto]"]`).val().replace(',', '.');
        $('#edProdModal').modal('show');
        // joga de volta nos inputs
        $("#id_cod_produto").val(cod);
        $("#id_cod_produto").prop("disabled", true);
        $("#add-prod").prop("readonly", true);
        $("#id_desc_prod").val(prod);
        $("#id_quantidade").val(qtd);
        $("#id_preco_unit").val(preco);
        $("#id_desconto").val(dsct);
        $("#id_unidProduto").val(unidadeTmp);
        $("#id_grupoProd").val(grupoTmp);
        $('#edProdModal').on('shown.bs.modal', function () {
            $('#id_preco_unit').trigger('focus');
        });
        $.ajax({
            url: '/produtos/lista_ajax/',
            method: 'GET',
            data: {
                s: cod,
                tp: 'cod',
                tp_prod: ''
            },
            success: function(response) {
                if (response.produtos.length > 0) {
                    const produto = response.produtos[0];
                    $('#id_unidProd').val(produto.unidProd);
                    $('#id_grupoProd').val(produto.grupo);
                    // Abre o modal
                    $('#edProdModal').modal('show');
                }
            },
            error: function() {
                toast("<i class='fa-solid fa-circle-xmark'></i> Erro ao buscar o produto. Tente novamente!", cor_vermelho);
            }
        });
    });
    // Notificações do Django
    function carregarNotificacoes() {
        $.get('/ajax/notificacoes/', function(response) {
            const notificacoes = response.notificacoes;
            const badge = $('.badge-pulse');
            const lista = $('#notificationsDropdown').next('ul.dropdown-menu');
            // Limpar a lista atual
            lista.empty();
            if (notificacoes.length > 0) {
                // Exibir badge
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
                            <a href="#"
                               class="abrir-modal-solicitacao dropdown-item text-wrap"
                               data-id="${n.solicitacao_id || ''}"
                               data-verb="${n.verb || ''}"
                               data-description="${n.description || ''}">
                                ${n.verb}
                                <br>
                                <small class="text-muted text-wrap">Mais informações, clique aqui!</small>
                            </a>
                        </li>
                    `);
                });
            } else {
                // Remove badge se não houver notificações
                badge.remove();
                lista.append(`
                    <li>
                        <a href="#" class="dropdown-item disabled text-center">Nenhuma notificação</a>
                    </li>
                `);
            }
        });
    }
    // 🔄 Atualiza a cada 30 segundos
    setInterval(carregarNotificacoes, 15000);
    // 🔥 E carrega imediatamente ao abrir a página
    $(document).ready(function() {
        carregarNotificacoes();
    });
    function toggleSenhaField() {
        if ($('#id_gerar_senha_lib').is(':checked')) {
            $('#id_senha_liberacao').prop('disabled', false);
        } else {
            $('#id_senha_liberacao').prop('disabled', true).val('');
        }
    }
    // Ajusta o estado ao carregar a página
    toggleSenhaField();
    // Ajusta o estado quando o switch for alterado
    $('#id_gerar_senha_lib').change(function() {
        toggleSenhaField();
    });
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
            acao: acaoSelecionada,
            usuario_id: usuarioId,
            csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
        }, function(data) {
            solicitacaoId = data.id;
            $('#userSelectModal').modal('hide');
            toastAguardando = Toastify({
                text: `<i class="fa-solid fa-stopwatch"></i> Aguardando aprovação para sua solicitação!
                       <div class='spinner-grow text-dark' role='status' style='width: 1rem; height: 1rem;'>
                       <span class='visually-hidden'Carregando...</span></div>`,
                duration: 180000,
                close: false,
                gravity: "top",
                position: "center",
                stopOnFocus: false,
                escapeMarkup: false,
                style: {
                    background: "linear-gradient(to right, #6c757d, #adb5bd)",
                    color: "#212529",
                    borderRadius: "8px"
                }
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
                if (toastAguardando) toastAguardando.hideToast();
                toast('<i class="fa-solid fa-hourglass-start"></i> Tempo expirado. A solicitação não foi respondida!', cor_info);
                return;
            }
            $.get(`/orcamentos/verificar-solicitacao/${solicitacaoId}/`, function(data) {
                if (data.status === 'Aprovada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast("<i class='fa-solid fa-circle-check'></i> Solicitação Concedida ao usuário!", cor_verde);
                    if (acaoSelecionada === "atribuir_desconto") {
                        $('#modalDesconto').modal('show');
                    } else if (acaoSelecionada === "atribuir_acrescimo") {
                        $('#modalAcrescimo').modal('show');
                    }
                } else if (data.status === 'Negada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast("<i class='fa-solid fa-circle-xmark'></i> Solicitação Negada ao usuário!", cor_vermelho);
                }
            });
        }, 5000);
    }
    $('#userSelectModal').on('show.bs.modal', function () {
        $.get('/orcamentos/usuarios-com-permissao/', function (data) {
            const select = $('#userSelect');
            select.empty();

            // opção padrão (sempre aparece)
            select.append(`<option value="">------</option>`);

            if (!data.usuarios || data.usuarios.length === 0) {
                select.append(`<option value="">Nenhum usuário disponível</option>`);
                return;
            }

            data.usuarios.forEach(u => {
                select.append(`<option value="${u.id}">${u.nome}</option>`);
            });
        });
    });
    // Ao clicar em uma notificação, abre o modal preenchendo descrição e id
    $(document).on('click', '.abrir-modal-solicitacao', function(e) {
        e.preventDefault();
        const verb = $(this).data('verb');
        const descricao = $(this).data('description') || '';
        $('#modalSolicitacaoLabel').text(verb);
        // Regex mais robusto para capturar o ID
        const match = verb.match(/ID\s+(\d+)/i);
        const solicitacaoId = match ? match[1] : null;
        console.log('ID capturado:', solicitacaoId);
        if (!solicitacaoId) {
            toast('<i class="fa-solid fa-exclamation"></i> ID da solicitação não encontrado!', cor_info);
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
    });
    // Função que envia o POST para a view Django que responde a solicitação
    function responderSolicitacao(id, acao) {
        console.log('Enviando resposta:', {id, acao});
        $.post('/orcamentos/responder-solicitacao/', {
            id: id,
            acao: acao,
            csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()
        }, function(response) {
            $('#modalSolicitacao').modal('hide');
            if (response.status === "Aprovada") {
                toast("<i class='fa-solid fa-circle-check'></i> Solicitação Concedida ao usuário!", cor_verde);
            } else {
                toast("<i class='fa-solid fa-circle-xmark'></i> Solicitação Negada ao usuário!", cor_vermelho);
            }
        });
    }
    function verificarOuCriarLocalizacao(estado, cidade, bairro) {
        return fetch(`/verificar-localizacao/?estado=${estado}&cidade=${cidade}&bairro=${bairro}`)
            .then(response => response.json())
            .catch(error => console.error('Erro na verificação de localizacao:', error));
    }
    // Marcar checkboxs de permissões
    $('.check-grupo').on('click', function () {
        const grupo = $(this).data('grupo');
        // Verifica se **todas** as permissões estão marcadas
        const todasMarcadas = $(`.check-permissao[data-grupo="${grupo}"]`).length === $(`.check-permissao[data-grupo="${grupo}"]:checked`).length;
        // Se todas marcadas, desmarca tudo, senão marca tudo
        $(`.check-permissao[data-grupo="${grupo}"]`).prop('checked', !todasMarcadas);
    });
    // Teste de Aviso de Permissão
    function verificarPermissaoAntesDeExecutar(perm, onPermitido, onNegado) {
        $.get('/usuarios/ajax/permissao/', { perm: perm }, function(data) {
            if (data.permitido) {
                onPermitido();
            } else {
                onNegado();
            }
        });
    }
    $('.btn-permissao').on('click', function (e) {
        e.preventDefault();
        const $btn = $(this);
        const permissao = $btn.data('permissao');
        const msgNegado = $btn.data('msg-negado') || 'Você não tem permissão para realizar essa ação!';
        const url = $btn.data('url');
        const href = $btn.attr('href');
        acaoSelecionada = $btn.data('acao');  // 🔥 pega a ação para o processo de solicitação
        verificarPermissaoAntesDeExecutar(
            permissao,
            function () {
                // === Ação permitida ===
                if (url) {
                    $('#loadingModal').modal('show');
                    $.post(url, function(response) {
                        location.reload();
                    }).fail(function () {
                        alert('Erro ao tentar executar a ação.');
                    });
                } else if (href) {
                    window.location.href = href;
                } else {
                    // Abre o modal diretamente se permitido
                    if (acaoSelecionada === "atribuir_desconto") {
                        $('#modalDesconto').modal('show');
                    } else if (acaoSelecionada === "atribuir_acrescimo") {
                        $('#modalAcrescimo').modal('show');
                    }
                }
            },
            function () {
                // === Ação negada ===
                $('#loadingModal').modal('hide');
                toast(`<i class="fa-solid fa-exclamation"></i> ${msgNegado}`, cor_amarelo);
                $('#confirmModal').modal('show');  // 👉 Abre o modal de confirmação para enviar a solicitação
            }
        );
    });
    // Contador de confirmação
    $('.modal').on('shown.bs.modal', function () {
        var modal = $(this);
        var btn = modal.find('.btn-confirmar');
        var contadorSpan = btn.find('.contador');
        var count = 3;
        btn.prop('disabled', true);
        contadorSpan.text(count);
        var intervalo = setInterval(function () {
            count--;
            if (count <= 0) {
                clearInterval(intervalo);
                contadorSpan.remove();
                btn.prop('disabled', false);
            } else {
                contadorSpan.text(count);
            }
        }, 1000);
        // Salva intervalo para limpar depois
        modal.data('intervalo', intervalo);
    });
    $('.modal').on('hidden.bs.modal', function () {
        var modal = $(this);
        var intervalo = modal.data('intervalo');
        if (intervalo) {
            clearInterval(intervalo);
            modal.removeData('intervalo');
        }
        var btn = modal.find('.btn-confirmar');
        btn.prop('disabled', true).append('<span class="contador">3</span>');
    });
    // Quando o botão for clicado
    $(document).on('click', '.btn-confirmar', function () {
        if ($(this).prop('disabled')) return;
        var $modal = $(this).closest('.modal');   // pega o modal onde o botão está
        var url = $(this).data('url');
        // fecha o modal
        $modal.modal('hide');
        // só redireciona depois que o modal terminar de fechar
        $modal.one('hidden.bs.modal', function () {
            window.location.href = url;
        });
    });
    // Consulta de Grupos
    function initGrupoSelect() {
        if ($('#id_grupo, #grupo, #grupo1, #campo-grupo-produto').length > 0) {
            $('#id_grupo, #grupo, #grupo1, #campo-grupo-produto').select2({
                placeholder: 'Selecione um grupo',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    inputTooShort: function() {
                        return 'Por favor, insira 1 ou mais caracteres';
                    },
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/grupos/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.grupos.map(function(grupo) {
                                return {
                                    id: grupo.id,
                                    text: grupo.nome_grupo
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initGrupoSelect();
    // Consulta de Regras de Grupo
    function initRegraSelect() {
        if ($('#id_regra').length > 0) {
            $('#id_regra').select2({
                placeholder: 'Selecione uma regra',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) return data.text;
                    return $(`
                        <div style="display:flex;flex-direction:column;line-height:1.2;">
                            <small class="text-muted">${data.codigo}</small>
                            <strong>${data.text}</strong>
                        </div>
                    `);
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    inputTooShort: function() {
                        return 'Por favor, insira 1 ou mais caracteres';
                    },
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/regras_produto/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.regras.map(function(regra) {
                                return {
                                    id: regra.id,
                                    text: regra.descricao,
                                    codigo: regra.codigo
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initRegraSelect();
    // Consulta de Tabelas de Preço
    function initTabPrecoSelect() {
        if ($('#id_tabela, #tb-prec').length > 0) {
            $('#id_tabela, #tb-prec').select2({
                placeholder: 'Selecione uma tabela',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    inputTooShort: function() {
                        return 'Por favor, insira 1 ou mais caracteres';
                    },
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/tabelas_preco/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.tabelas_preco.map(function(tabela_preco) {
                                return {
                                    id: tabela_preco.id,
                                    text: tabela_preco.descricao
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initTabPrecoSelect();
    // Consulta de Unidades
    function initUnidadeSelect() {
        if ($('#unidade, #unidade1, #campo-unidade-produto, #id_unidProd').length > 0) {
            $('#unidade, #unidade1, #campo-unidade-produto, #id_unidProd').select2({
                placeholder: 'Selecione uma unidade',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    inputTooShort: function() {
                        return 'Por favor, insira 1 ou mais caracteres';
                    },
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/unidades/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.unidades.map(function(unidade) {
                                return {
                                    id: unidade.id,
                                    text: unidade.nome_unidade
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initUnidadeSelect();
    // Consulta de Bancos
    function initBancoSelect() {
        if ($('#id_banco_fil').length > 0) {
            $('#id_banco_fil').select2({
                placeholder: 'Selecione um banco',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    inputTooShort: function() {
                        return 'Por favor, insira 1 ou mais caracteres';
                    },
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/bancos/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.bancos.map(function(banco) {
                                return {
                                    id: banco.id,
                                    text: banco.nome_banco
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initBancoSelect();
    // Consulta de Filiais depois do usuário estiver logado
    function initFilialSelect() {
        if ($('#id_filial_user, #id_vinc_fil').length > 0) {
            $('#id_filial_user, #id_vinc_fil').select2({
                placeholder: 'Selecione uma filial',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    inputTooShort: function() {
                        return 'Por favor, insira 1 ou mais caracteres';
                    },
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/filiais/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.filiais.map(function(filial) {
                                return {
                                    id: filial.id,
                                    text: filial.fantasia
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initFilialSelect();
    // Consulta de Marcas
    function initMarcaSelect() {
        if ($('#id_marca, #marca, #marca1').length > 0) {
            $('#id_marca, #marca, #marca1').select2({
                placeholder: 'Selecione uma marca',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    inputTooShort: function() {
                        return 'Por favor, insira 1 ou mais caracteres';
                    },
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/marcas/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.marcas.map(function(marca) {
                                return {
                                    id: marca.id,
                                    text: marca.nome_marca
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initMarcaSelect();
    // Consulta de Formas de Pagamento
    function initFormaPgtoSelect() {
        if ($('#id_formas_pgto, #id_form_pgto').length > 0) {
            $('#id_formas_pgto, #id_form_pgto').select2({
                placeholder: 'Selecione uma forma',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/formas_pgto/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.formas_pgto.map(function(forma_pgto) {
                                return {
                                    id: forma_pgto.id,
                                    text: forma_pgto.descricao
                                };
                            })
                        };
                    },
                    cache: true
                }
            }).on('select2:open', function () {
                setTimeout(function() {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 50);
            });
        }
    }
    initFormaPgtoSelect();
    // Consulta de Tipos de Cobranças
    function initTpCobSelect() {
        if ($('#selTpCob').length > 0) {
            $('#selTpCob').select2({
                placeholder: 'Selecione um tipo',
                allowClear: true,
                templateResult: function (data) {
                    if (!data.id) {
                        return data.text;
                    }
                    // cria o layout: ID em cima e Nome abaixo
                    var $container = $(`
                        <div style="display: flex; flex-direction: column; line-height: 1.2;">
                            <span style="font-size: 14px;">${data.id}</span><br>
                            <strong style="font-size: 14px;">${data.text}</strong>
                        </div>
                    `);
                    return $container;
                },
                templateSelection: function (data) {
                    // mostra apenas o nome após selecionar
                    return data.text;
                },
                language: {
                    noResults: function() {
                        return 'Nenhum resultado encontrado';
                    },
                    searching: function() {
                        return 'Procurando...';
                    }
                },
                ajax: {
                    url: '/tp_cobrancas/lista_ajax/',
                    dataType: 'json',
                    delay: 250,
                    data: function(params) {
                        return { term: params.term };
                    },
                    processResults: function(data) {
                        return {
                            results: data.tp_cobrancas.map(function(tp_cobranca) {
                                return {
                                    id: tp_cobranca.id,
                                    text: tp_cobranca.descricao
                                };
                            })
                        };
                    },
                    cache: true
                }
            });
        }
    }
    initTpCobSelect();
    // Teste
    if ($('#id_desconto, #id_acrescimo, #total-frete') === "") {
        $('#id_desconto, #id_acrescimo, #total-frete').val("0.00");
    }
    function addDtInterv(dataString, intervalo) {
        // Converte a string da data no formato "DD/MM/AAAA" para um objeto Date
        const [dia, mes, ano] = dataString.split('/').map(Number);
        const data = new Date(ano, mes - 1, dia);
        // Adiciona os dias do intervalo
        data.setDate(data.getDate() + Number(intervalo));
        // Formata a nova data para "DD/MM/AAAA"
        const novoDia = data.getDate().toString().padStart(2, '0');
        const novoMes = (data.getMonth() + 1).toString().padStart(2, '0');
        const novoAno = data.getFullYear();
        return `${novoDia}/${novoMes}/${novoAno}`;
    }
    let toastErrorShown = false;
    $(document).on('input', '.alt', function () {
        let porta = $(this).data('porta');
        $(`.alt-corte[data-porta="${porta}"]`).val($(this).val());
    });
    function iniciarLoading() {
        $("#loadingModal").modal({
            backdrop: 'static',
            keyboard: false
        }).modal("show");
    }
    let loadingTimeout = null;
    function finalizarLoading() {
        if (loadingTimeout) {
            clearTimeout(loadingTimeout);
        }
        loadingTimeout = setTimeout(() => {
            $("#loadingModal").modal("hide");
            loadingTimeout = null;
        }, 2500);
    }
    function arredondarParaCima(valor, casasDecimais) {
        let fator = Math.pow(10, casasDecimais);
        return (Math.ceil(valor * fator) / fator).toFixed(casasDecimais);
    }
    function arredondarComAjuste(valor) {
        let arredondado = parseFloat(valor.toFixed(2));
        let decimal = arredondado % 1;
        if (decimal >= 0.480 && decimal < 0.495) {
            arredondado = Math.floor(arredondado) + 0.50;
        }
        return arredondado.toFixed(2);
    }
    function arredondarInteiro(valor) {
        let num = parseFloat(valor);
        if (isNaN(num)) return "";
        let inteiro = Math.floor(num);            // parte inteira
        let decimal = num - inteiro;              // parte decimal
        if (decimal > 0.50) {
            return inteiro + 1;                   // passa de .50 -> sobe 1
        } else {
            return inteiro;                       // até .50 -> mantém inteiro
        }
    }
    function calcFtPeso(porta) {
        let alt_corte = parseFloat(
            $(`.alt-corte[data-porta="${porta}"]`).val().replace(',', '.')
        );
        let tp_vao = $(`.tipo-vao[data-porta="${porta}"]`).val();
        if (isNaN(alt_corte)) {
            $(`.ft-peso[data-porta="${porta}"]`).val('');
            return;
        }
        let resultado;
        if (tp_vao === "Fora do Vão") {
            resultado = (alt_corte + 0.6) / 7.5;
        } else if (tp_vao === "Dentro do Vão") {
            resultado = (alt_corte - 0.6) / 7.5;
        }
        let final = arredondarParaCima(resultado, 2) * 100;
        $(`.ft-peso[data-porta="${porta}"]`).val(final.toFixed(2));
    }
    function calcLgCorte(porta) {
        let largRaw = $(`.larg[data-porta="${porta}"]`).val();
        if (!largRaw) return "";
        let larg = parseFloat(largRaw.replace(/,/g, ""));
        if (isNaN(larg)) return "";
        const tp_vao = $(`.tipo-vao[data-porta="${porta}"]`).val();
        let calc = 0;
        if (tp_vao === "Fora do Vão") {
            calc = larg + 0.10;
        } else if (tp_vao === "Dentro do Vão") {
            calc = larg - 0.08;
        } else if (tp_vao === '1 Lado Dentro do Vão') {
            calc = larg + 0.03;
        }
        $(`.larg-corte[data-porta="${porta}"]`).val(calc.toFixed(2));
    }
    function calcPeso(porta) {
        let larg_corte = parseFloat($(`.larg-corte[data-porta="${porta}"]`).val()) || 0;
        let ft_peso = parseFloat($(`.ft-peso[data-porta="${porta}"]`).val()) || 0;
        const calculo = (larg_corte * 0.8) * ft_peso * 1.2;
        const pesoFinal = arredondarParaCima(calculo, 0);
        $(`.peso[data-porta="${porta}"]`).val(pesoFinal);
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
    function selecionarMotorPorPeso(peso, regraJSON) {
        for (const r of regraJSON) {
            if (peso <= r.max) return r.produto;
        }
        return null;
    }
    let motorCtrl = {};
    async function buscarMotorIdeal(porta) {
        const peso = parseFloat($(`.peso[data-porta="${porta}"]`).val()) || 0;
        if (peso <= 0) return;
        motorCtrl[porta] ??= { ultimoProduto: null, ultimoPeso: null };
        const regra = REGRAS['MOTOR_PESO'];
        if (!regra) return;
        const regraJSON = JSON.parse(regra.expressao);
        const nomeMotor = selecionarMotorPorPeso(peso, regraJSON);
        if (!nomeMotor) return;
        const ctrl = motorCtrl[porta];
        if (ctrl.ultimoProduto === nomeMotor && ctrl.ultimoPeso === peso) {
            return;
        }
        removerProdutoPorRegra(porta, 'MOTOR_PESO');
        return new Promise((resolve, reject) => {
            $.get('/produtos/lista_ajax/', {
                s: nomeMotor,
                tp: 'desc',
                tp_prod: 'Principal'
            })
            .done(resp => {
                prodManager.data[porta] ??= [];
                const p = resp.produtos?.[0];
                if (!p) {
                    resolve();
                    return;
                }
                prodManager.data[porta].push({
                    id: p.id,
                    cod: p.id,
                    desc: p.desc_prod,
                    unid: p.unidProd,
                    vl_compra: parseFloat(p.vl_compra),
                    vl_unit: parseFloat(p.vl_prod),
                    qtd: 1,
                    qtd_manual: false,
                    total: p.vl_prod,
                    regra: p.regra,
                    ativo: true
                });
                $(`#tblProd_${porta} tbody`).append(`
                    <tr data-porta="${porta}" data-item-id="${p.id}">
                        <td data-label="Código:" class="td-cod mobile-full">${p.id}</td>
                        <td data-label="Descrição:" class="td-desc mobile-full">${p.desc_prod}</td>
                        <td data-label="Unidade:" class="td-unid mobile-full">${p.unidProd}</td>
                        <td class="td-vl-compra text-danger fw-bold mobile-full" data-label="Vl. Compra:">${p.vl_compra}</td>
                        <td class="vl-unit text-success fw-bold mobile-full" data-label="Vl. Unit:">${p.vl_prod}</td>
                        <td class="qtd-produto mobile-full" data-label="Quantidade:">0.00</td>
                        <td class="tot-compra text-danger fw-bold mobile-full" data-label="Tot. Compra:">0.00</td>
                        <td class="vl-total text-success fw-bold mobile-full" data-label="Vl. Total:">0.00</td>
                        <td data-label="Ações:" class="mobile-full">
                            <i class="fas fa-edit editBtn" style="color: #13c43f; cursor:pointer;" data-bs-toggle="modal" data-bs-target="#editItemModal"></i>
                            <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor:pointer;"></i>
                        </td>
                    </tr>
                `);
                ctrl.ultimoProduto = nomeMotor;
                ctrl.ultimoPeso = peso;
                atualizarJSONPortas();
                resolve(); // ✅ motor pronto
            })
            .fail(err => reject(err));
        });
    }
    function removerProdutoPorRegra(porta, codigoRegra) {
        if (!prodManager.data?.[porta]) return;
        prodManager.data[porta] = prodManager.data[porta].filter(i => {
            if (i.regra?.codigo === codigoRegra) {
                $(`#tblProd_${porta} tbody tr[data-item-id="${i.id}"]`).remove();
                return false;
            }
            return true;
        });
    }
    function resetarControleRegras() {
        motorCtrl = {};
    }
    function removerPinturasDaPorta(porta) {
        const mapa = obterMapaSelecao(REGRAS.PINTURA_TIPO);
        const descricoes = Object.values(mapa)
            .map(d => d.toUpperCase().trim());
        prodAdcManager.data[porta] = (prodAdcManager.data[porta] || []).map(item => {
            if (descricoes.includes(item.desc?.toUpperCase())) {
                item.ativo = false;
                item.qtd_final = 0;
                item.qtd_calc = 0;
            }
            return item;
        });
        $(`#tblAdc_${porta} tbody tr`).each(function () {
            const desc = $(this).find('.td-desc').text().toUpperCase().trim();
            if (descricoes.includes(desc)) {
                $(this).remove();
            }
        });
        atualizarTabelaPorta(porta);
        atualizarSubtotal();
        atualizarJSONPortas();
    }
    toastErrorShown = false;
    function obterMapaSelecao(regra) {
        try {
            return JSON.parse(regra.expressao || '{}');
        } catch (e) {
            console.error('Regra SELECAO inválida', regra.expressao);
            return {};
        }
    }
    function isProdutoLamina(item) {

        const regra = REGRAS.LAMINA_TIPO;
        if (!regra || regra.tipo !== 'SELECAO') return false;

        let mapa = {};
        try {
            mapa = JSON.parse(regra.expressao || '{}');
        } catch {
            return false;
        }

        const descricoesLamina = Object.values(mapa)
            .map(d => d.toUpperCase().trim());

        // 1️⃣ regra_origem explícita
        if (item.regra_origem === 'LAMINA_TIPO') return true;

        // 2️⃣ produto veio do backend sem origem, mas é lâmina
        if (item.desc && descricoesLamina.includes(item.desc.toUpperCase().trim())) {
            return true;
        }

        return false;
    }
    function removerLaminaTipo(porta) {

        prodManager.data[porta] = (prodManager.data[porta] || []).filter(item => {
            // 🔥 remove QUALQUER lâmina (backend ou frontend)
            return !isProdutoLamina(item);
        });

        // remove do DOM também
        $(`#tblProd_${porta} tbody tr[data-regra-origem="LAMINA_TIPO"]`).remove();
    }

    function atualizarLaminarPorta(porta) {

        const valorSelecionado = $(`.tipo-lamina[data-porta="${porta}"]`).val();
        const regraSelecao = REGRAS.LAMINA_TIPO;

        if (!regraSelecao || regraSelecao.tipo !== 'SELECAO') return;

        const mapa = obterMapaSelecao(regraSelecao);
        const descAtiva = (mapa[valorSelecionado] || '').toUpperCase().trim();

        if (!descAtiva) return;

        prodManager.data[porta] ??= [];

        // 🔥 SEMPRE remove primeiro
        removerLaminaTipo(porta);

        // 🔥 Depois insere a nova
        inserirLaminaSelecionada(porta);
    }
    const laminaEmProcesso = {};
    function inserirLaminaSelecionada(porta) {
        // 🔒 BLOQUEIO DE CONCORRÊNCIA
        if (laminaEmProcesso[porta]) {
            console.warn('Lâmina já em processamento para porta', porta);
            return;
        }
        laminaEmProcesso[porta] = true;
        const laminaAtiva = getDescricaoLaminaAtiva(porta);
        if (!laminaAtiva) return;
        const descUpper = laminaAtiva.toUpperCase().trim();

        // 🔥 REMOVE QUALQUER LÂMINA DO DOM (backend ou frontend)
        $(`#tblProd_${porta} tbody tr`).each(function () {
            const desc = $(this).find('.td-desc').text().toUpperCase().trim();
            if (desc === descUpper) {
                $(this).remove();
            }
        });
        prodManager.data[porta] ??= [];
        $.get('/produtos/lista_ajax/', {
            tp: 'desc',
            tp_prod: 'Principal',
            s: laminaAtiva
        }).done(resp => {
            const p = resp.produtos?.[0];
            if (!p) return;
            const item = {
                id: p.id,
                cod: p.id,
                desc: p.desc_prod,
                unid: p.unidProd,
                vl_compra: Number(p.vl_compra),
                vl_unit: Number(p.vl_prod),
                qtd_calc: 0,
                qtd_final: 0,
                qtd_manual: false,
                regra: p.regra,
                ativo: true,
                regra_origem: 'LAMINA_TIPO'
            };
            if (p.regra?.tipo?.toUpperCase() === 'QTD') {
                try {
                    const portaData = {
                        largura: getFloat(`.larg[data-porta="${porta}"]`),
                        altura: getFloat(`.alt[data-porta="${porta}"]`),
                        larg_c: getFloat(`.larg-corte[data-porta="${porta}"]`),
                        alt_c: getFloat(`.alt-corte[data-porta="${porta}"]`),
                        m2: getFloat(`.m2[data-porta="${porta}"]`)
                    };
                    const qtd = Function(
                        ...Object.keys(portaData),
                        `return ${p.regra.expressao};`
                    )(...Object.values(portaData));
                    const qtdFloat = parseFloat(String(qtd).replace(',', '.'));
                    item.qtd_calc = qtdFloat || 0;
                    item.qtd_final = qtdFloat || 0;
                } catch (e) {
                    console.error('Erro ao calcular quantidade da regra:', e);
                }
            }
            prodManager.data[porta].push(item);
            const trHtml = `
                <tr data-porta="${porta}" data-item-id="${item.id}" data-regra-origem="LAMINA_TIPO">
                    <td data-label="Código:" class="td-cod mobile-full">${item.cod}</td>
                    <td data-label="Descrição:" class="td-desc mobile-full">${item.desc}</td>
                    <td data-label="Unidade:" class="td-unid mobile-full">${item.unid}</td>
                    <td class="td-vl-compra text-danger fw-bold mobile-full" data-label="Vl. Compra:">
                        ${item.vl_compra.toFixed(2)}
                    </td>
                    <td class="vl-unit text-success fw-bold mobile-full" data-label="Vl. Unit:">
                        ${item.vl_unit.toFixed(2)}
                    </td>
                    <td class="qtd-produto mobile-full" data-label="Quantidade:">
                        ${item.qtd_final.toFixed(2)}
                    </td>
                    <td class="tot-compra text-danger fw-bold mobile-full" data-label="Tot. Compra:">0,00</td>
                    <td class="vl-total text-success fw-bold mobile-full" data-label="Vl. Total:">0,00</td>
                    <td data-label="Ações:" class="mobile-full">
                        <i class="fas fa-edit editBtn" style="color:#13c43f;cursor:pointer"
                        data-bs-toggle="modal" data-bs-target="#editItemModal"></i>
                        <i class="fas fa-trash deleteBtn" style="color:#db1e47;cursor:pointer"></i>
                    </td>
                </tr>
            `;
            $(`#tblProd_${porta} tbody`).append(trHtml);
            const tr = $(`#tblProd_${porta} tbody tr[data-item-id="${item.id}"]`);
            const totCompra = item.qtd_final * item.vl_compra;
            const vlTotal = item.qtd_final * item.vl_unit;
            tr.find('.tot-compra').text(totCompra.toFixed(2).replace('.', ','));
            tr.find('.vl-total').text(vlTotal.toFixed(2).replace('.', ','));
            atualizarSubtotal();
            atualizarJSONPortas();
            reposicionarLaminaPrimeiro(porta);
        }).always(() => {
            laminaEmProcesso[porta] = false; // 🔓 libera
        });
    }
    function atualizarPinturaPorta(porta) {
        const temPintura = $('#id_pintura').val();
        const mapa = obterMapaSelecao(REGRAS.PINTURA_TIPO);
        const descricoesPintura = Object.values(mapa).map(d => d.toUpperCase().trim());
        prodAdcManager.data[porta] ??= [];
        if (temPintura === 'Não') {
            prodAdcManager.data[porta] = prodAdcManager.data[porta].filter(i => i.regra_origem !== 'PINTURA_TIPO');
            $(`#tblAdc_${porta} tbody tr`).each(function() {
                const desc = $(this).find('.td-desc').text().toUpperCase().trim();
                if (descricoesPintura.includes(desc)) $(this).remove();
            });
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            atualizarJSONPortas();
            return;
        }
        const valorSelecionado = $('#id_tp_pintura').val();
        const descAtiva = (mapa[valorSelecionado] || '').toUpperCase().trim();
        if (!descAtiva) return;
        prodAdcManager.data[porta] = prodAdcManager.data[porta].filter(i => i.regra_origem !== 'PINTURA_TIPO');
        $(`#tblAdc_${porta} tbody tr`).each(function() {
            const desc = $(this).find('.td-desc').text().toUpperCase().trim();
            if (descricoesPintura.includes(desc)) $(this).remove();
        });
        inserirPinturaSelecionada(porta, descAtiva);
    }
    function inserirPinturaSelecionada(porta, pinturaAtiva) {
        if (!pinturaAtiva) return;
        prodAdcManager.data[porta] ??= [];
        $.get('/produtos/lista_ajax/', { tp:'desc', tp_prod:'Adicional', s:pinturaAtiva })
        .done(resp => {
            const p = resp.produtos?.[0];
            if (!p) return;
            const item = {
                id: p.id, cod: p.id, desc: p.desc_prod, unid: p.unidProd,
                vl_compra: Number(p.vl_compra), vl_unit: Number(p.vl_prod),
                qtd_calc: 0, qtd_final: 0, qtd_manual: false, regra: p.regra,
                ativo: true, regra_origem: 'PINTURA_TIPO'
            };
            if (p.regra?.tipo?.toUpperCase() === 'QTD') {
                try {
                    const portaData = {
                        largura: getFloat(`.larg[data-porta="${porta}"]`),
                        altura: getFloat(`.alt[data-porta="${porta}"]`),
                        larg_c: getFloat(`.larg-corte[data-porta="${porta}"]`),
                        alt_c: getFloat(`.alt-corte[data-porta="${porta}"]`),
                        m2: getFloat(`.m2[data-porta="${porta}"]`)
                    };
                    const qtd = Function(...Object.keys(portaData), `return ${p.regra.expressao};`)(...Object.values(portaData));
                    const qtdFloat = parseFloat(String(qtd).replace(',', '.')) || 0;
                    item.qtd_calc = item.qtd_final = qtdFloat;
                } catch(e) { console.error('Erro ao calcular pintura:', e); }
            }
            prodAdcManager.data[porta].push(item);
            const trHtml = `<tr data-porta="${porta}" data-item-id="${item.id}" data-regra-origem="PINTURA_TIPO">
                <td data-label="Código:" class="td-cod mobile-full">${item.cod}</td>
                <td data-label="Descrição:" class="td-desc mobile-full">${item.desc}</td>
                <td data-label="Unidade:" class="td-unid mobile-full">${item.unid}</td>
                <td class="td-vl-compra text-danger fw-bold mobile-full" data-label="Vl. Compra:">${item.vl_compra.toFixed(2)}</td>
                <td class="vl-unit text-success fw-bold mobile-full" data-label="Vl. Unit:">${item.vl_unit.toFixed(2)}</td>
                <td class="qtd-produto mobile-full" data-label="Quantidade:">${item.qtd_final.toFixed(2)}</td>
                <td class="tot-compra text-danger fw-bold mobile-full" data-label="Tot. Compra:">0,00</td>
                <td class="vl-total text-success fw-bold mobile-full" data-label="Vl. Total:">0,00</td>
                <td><i class="fas fa-edit editBtn" style="color:#13c43f;cursor:pointer" data-bs-toggle="modal" data-bs-target="#editItemAdcModal"></i>
                    <i class="fas fa-trash deleteBtn" style="color:#db1e47;cursor:pointer"></i>
                </td>
            </tr>`;
            $(`#tblAdc_${porta} tbody`).append(trHtml);
            const totCompra = item.qtd_final * item.vl_compra;
            const vlTotal = item.qtd_final * item.vl_unit;
            const tr = $(`#tblAdc_${porta} tbody tr[data-item-id="${item.id}"]`);
            tr.find('.tot-compra').text(totCompra.toFixed(2));
            tr.find('.vl-total').text(vlTotal.toFixed(2));
            atualizarSubtotal();
            atualizarJSONPortas();
        });
    }
    
    $(document).on("change", ".tipo-lamina", function () {
        iniciarLoading();
        atualizarLaminarPorta($(this).data("porta"));
        finalizarLoading();
    });
    $(document).on('keyup change', '.larg', function () {
        let porta = $(this).data('porta');
        calcLgCorte(porta);
    });
    // $(document).on('change', '.tipo-vao', function () {
    //     let porta = $(this).data('porta');
    //     iniciarLoading();
    //     calcLgCorte(porta); // 1️⃣ define larg-corte
    //     calcFtPeso(porta);            // 2️⃣ define ft-peso
    //     calcM2(porta);                // 3️⃣ usa larg-corte correta
    //     calcQtdLam(porta);            // 4️⃣ independente
    //     calcularEixoMotor(porta);
    //     calcPeso(porta);
    //     atualizarLaminarPorta(porta);
    //     atualizarPinturaPorta(porta);
    //     atualizarTabelaPorta(porta);
    //     atualizarSubtotal();
    //     atualizarJSONPortas();
    //     gerarJSONFormas();
    //     finalizarLoading();
    // });
    function forcarRecalculoPorLargCorte(porta, larg_c) {

        larg_c = Number(larg_c) || 0;

        (prodManager.data[porta] || []).forEach(item => {
            if (!item.regra || item.regra.tipo !== 'QTD') return;

            if (
                item.regra.codigo === 'EIXO_LARGURA' ||
                item.regra.codigo === 'SOLEIRA_LARGURA'
            ) {
                item.qtd_manual = false;
                item.qtd_calc = larg_c;
                item.qtd_final = larg_c;
                item.ativo = larg_c > 0;

                console.log('RECALC LARG_C OK:', item.cod, larg_c);
            }
        });
    }

    $(document).on('change', '.tipo-vao', async function() {
        iniciarLoading();
        const promises = [];
        $('[id^="tblProd_"]').each(function() {
            const porta = $(this).attr('id').split('_')[1];
            calcLgCorte(porta); // 1️⃣ define larg-corte
            // 🔥 PEGAR DA FONTE CERTA
            const larg_c = Number(medidasCtrl[porta]?.larg_c)
                        || parseFloat($(`.larg-corte[data-porta="${porta}"]`).val())
                        || 0;

            forcarRecalculoPorLargCorte(porta, larg_c);
            calcFtPeso(porta);            // 2️⃣ define ft-peso
            calcM2(porta);                // 3️⃣ usa larg-corte correta
            calcQtdLam(porta);            // 4️⃣ independente
            calcularEixoMotor(porta);
            calcPeso(porta);
            atualizarLaminarPorta(porta);
            atualizarPinturaPorta(porta);
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            atualizarJSONPortas();
            gerarJSONFormas();
            reindexarPortas();
        });
        await Promise.all(promises);
        finalizarLoading();
    });
    $("#prod_servBtn, #adicionaisBtn, #form_pgtoBtn").on("click", function () {
        atualizarSubtotal();
        calcularValorForma();
        somaFormas();
        atualizarJSONPortas();
        gerarJSONFormas();
    });
    // function desativarPinturas(porta) {
    //     const mapaPinturas = Object.values(obterMapaSelecao(REGRAS.PINTURA_TIPO))
    //         .map(d => d.toUpperCase().trim());

    //     prodAdcManager.data[porta] = (prodAdcManager.data[porta] || [])
    //         .filter(item => !descricoesPintura.includes(item.desc?.toUpperCase()));

    // }
    function limparPinturas(porta) {
        const mapaPinturas = Object.values(obterMapaSelecao(REGRAS.PINTURA_TIPO))
            .map(d => d.toUpperCase().trim());

        // remove do manager
        prodAdcManager.data[porta] = (prodAdcManager.data[porta] || [])
            .filter(i => i.regra_origem !== 'PINTURA_TIPO');

        // remove do DOM
        $(`#tblAdc_${porta} tbody tr`).each(function() {
            const desc = $(this).find('.td-desc').text().toUpperCase().trim();
            if (mapaPinturas.includes(desc)) $(this).remove();
        });

        atualizarSubtotal();
        atualizarJSONPortas();
    }
    function limparLaminas(porta) {
        const mapaLaminas = Object.values(obterMapaSelecao(REGRAS.LAMINA_TIPO))
            .map(d => d.toUpperCase().trim());

        // remove do manager
        prodManager.data[porta] = (prodManager.data[porta] || [])
            .filter(i => i.regra_origem !== 'LAMINA_TIPO');

        // remove do DOM
        $(`#tblProd_${porta} tbody tr`).each(function() {
            const desc = $(this).find('.td-desc').text().toUpperCase().trim();
            if (mapaLaminas.includes(desc)) $(this).remove();
        });
        atualizarSubtotal();
        atualizarJSONPortas();
    }

    $(document).on('change', '#id_pintura, #id_tp_pintura', async function() {
        iniciarLoading();
        const temPintura = $(this).val();
        const mapaPinturas = Object.values(obterMapaSelecao(REGRAS.PINTURA_TIPO)).map(d => d.toUpperCase().trim());
        const promises = [];

        $('[id^="tblAdc_"]').each(function() {
            const porta = $(this).attr('id').split('_')[1];
            if (temPintura === 'Não') {
                limparPinturas(porta);
            } else {
                atualizarPinturaPorta(porta);
            }
        });

        await Promise.all(promises);
        if (temPintura !== 'Não') {
            atualizarSubtotal();
            atualizarJSONPortas();
        }
        gerarJSONFormas();
        reindexarPortas();
        finalizarLoading();
    });


    gerarJSONFormas();
    let debounceTimeout;
    function atualizarCalculoCompletoDebounced() {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            calcFtPeso();
            // calcularValor();
        }, 200);
    }
    $('#id_alt, #id_tp_vao, #id_larg, #id_qtd, #id_rolo, #id_alt_corte, #id_larg_corte').on('blur', atualizarCalculoCompletoDebounced);
    $('#desconto, #acrescimo').mask('000.000.000.000.000,00', {reverse: true});
    $('#id_vl_prod, #id_vl_prod_adc, #editValorItemInput, #editValorItemAdcInput, .editable, .inpFrete, #id_vl_form_pgto, #id_desconto, #id_acrescimo').mask('00000.00', {reverse: true});
    $('#editQtdInput, #editQtdAdcInput, #id_qtd_prod, #id_qtd_prod_adc, #id_vl_compra').mask('000,000.00', {reverse: true});
    $('.larg, .alt, .id_larg, .larg-corte, .alt-corte, .qtd-laminas, .m2').mask('000,000.00', {reverse: true});
    $('#id_vl_p_s').mask('000.00', {reverse: true});
    // Função para converter valor em formato brasileiro para float
    var desconto = 0;
    var total = 0;

    function atualizarSubtotal() {
        return new Promise(resolve => {

            let subtotal   = 0;
            let custoTotal = 0;
            let vl_p_s = parseFloat(
                String($('#id_vl_p_s').val() || '0')
                    .replace(/\./g, '')
                    .replace(',', '.')
            ) || 0;

            // ===== PRODUTOS E ADICIONAIS (TABELA) =====
            $('[id^="tblProd_"] tbody tr, [id^="tblAdc_"] tbody tr').each(function () {

                const compraTxt = $(this).find('.tot-compra').text().trim();
                const vendaTxt  = $(this).find('.vl-total').text().trim();

                const compra = parseValor(compraTxt);
                const venda  = parseValor(vendaTxt);


                custoTotal += compra;
                subtotal   += venda;
            });

            subtotal += vl_p_s;

            // ===== UI =====
            $('#custoTotal_txt').text(
                'R$ ' + custoTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
            );

            $('#subtotal_txt').text(
                'R$ ' + subtotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
            );

            $('#id_subtotal').val(subtotal.toFixed(2));
            $('#id_vl_form_pgto').val(subtotal.toFixed(2));

            // ===== DESCONTO / ACRÉSCIMO =====
            const descontoRaw = $('#id_desconto').length
                ? $('#id_desconto').val()
                : '0';

            const acrescimoRaw = $('#id_acrescimo').length
                ? $('#id_acrescimo').val()
                : '0';

            const desconto  = parseValor(descontoRaw);
            const acrescimo = parseValor(acrescimoRaw);

            const total = subtotal - desconto + acrescimo;

            $('#desconto').text(
                'R$ ' + desconto.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
            );

            $('#acrescimo').text(
                'R$ ' + acrescimo.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
            );

            $('#total_txt').text(
                'R$ ' + total.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
            );

            $('#id_total').val(total.toFixed(2));

            const margemLucro = subtotal > 0
                ? ((subtotal - custoTotal) / subtotal) * 100
                : 0;

            $('#margem_txt').text(margemLucro.toFixed(2) + '%');

            calcularValorForma();
            somaFormas();

            resolve();
        });
    }


    atualizarSubtotal();
    function parseValor(valor) {
        if (!valor) return 0;
        let limpo = valor.toString().replace(/[R$\s]/g, '').replace(/\./g, '').replace(',', '.');
        return parseFloat(limpo) || 0;
    }
    function calcularValorForma() {
        const totalValor = parseValor($('#id_total').val() || $('#total_txt').text());
        let totalPago = 0;
        $('#itensTableForm tbody tr').each(function() {
            const valor = parseValor($(this).find('td:nth-child(3)').text());
            totalPago += valor;
        });
        let restante = totalValor - totalPago;
        // arredondar para 2 casas
        restante = Math.max(0, Math.round(restante * 100) / 100);
        $('#id_vl_form_pgto').val(restante.toFixed(2));
    }
    function verificarTotalFormas() {
        const totalValor = parseValor($('#id_total').val() || $('#total_txt').text());
        let totalFormas = 0;
        $('#itensTableForm tbody tr').each(function () {
            totalFormas += parseValor($(this).find('td:nth-child(3)').text());
        });
        // arredondar
        const totalArred = parseFloat(totalValor.toFixed(2));
        const formasArred = parseFloat(totalFormas.toFixed(2));
        $("#somaFormas").text(formasArred.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
        // comparação com tolerância mínima
        if (Math.abs(totalArred - formasArred) > 0.01) {
            $('#form_pgtoBtn').click();  // exibe modal de erro, se necessário
            return false;
        }
        return true;
    }
    function somaFormas() {
        let soma = 0;
        const linhas = $('#itensTableForm tbody tr').filter(function () {
            return $(this).find('td').length > 0;
        });
        if (linhas.length === 0) {
            $("#somaFormas").text("R$ 0,00");
            return true;
        }
        linhas.each(function () {
            const valor = parseValor($(this).find('td:nth-child(3)').text());
            soma += valor;
        });
        const total = parseFloat(soma.toFixed(2));
        $("#somaFormas").text(
            "R$ " + total.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        );
        return true;
    }
    // Atualização ao digitar
    $('#id_desconto, #id_acrescimo').on('input', function () {
        atualizarSubtotal();
        calcularValorForma();
        somaFormas();
    });
    function gerarPortas() {
        const qtd = parseInt($('#qtd_portas').val());
        if (isNaN(qtd) || qtd < 1) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Informe uma quantidade válida de Portas!", cor_amarelo);
            return;
        }

        // 🔥 RESET TOTAL DE ESTADO
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
                    <td data-label="Larg.:" class="mobile-2col"><input type="text" class="form-control form-control-sm larg" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Alt.:" class="mobile-2col"><input type="text" class="form-control form-control-sm alt" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Lg. Corte:" class="mobile-2col"><input readonly class="form-control form-control-sm larg-corte" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="At. Corte:" class="mobile-2col"><input readonly class="form-control form-control-sm alt-corte" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Qtd. Lâm.:" class="mobile-2col"><input readonly class="form-control form-control-sm qtd-laminas" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="M²:" class="mobile-2col"><input readonly class="form-control form-control-sm m2" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Ft. Peso:" class="mobile-2col"><input readonly class="form-control form-control-sm ft-peso" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Peso:" class="mobile-2col"><input readonly class="form-control form-control-sm peso" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Eix. Mot.:" class="mobile-2col"><input readonly class="form-control form-control-sm eix-mot" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Rolo:" class="mobile-full"><input readonly class="form-control form-control-sm rolo" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Tp. Lâm.:" class="mobile-full">
                        <select class="form-select form-select-sm tipo-lamina" data-porta="${i}">
                            <option value="Fechada">Fechada</option>
                            <option value="Transvision">Transvision</option>
                        </select>
                    </td>
                    <td data-label="Tp. Vão:" class="mobile-full">
                        <select class="form-select form-select-sm tipo-vao" data-porta="${i}">
                            <option value="Fora do Vão">Fora do Vão</option>
                            <option value="Dentro do Vão">Dentro do Vão</option>
                            <option value="1 Lado Dentro do Vão">1 Lado Dentro do Vão</option>
                        </select>
                    </td>
                    <td data-label="Exc.:" class="text-center mobile-full">
                        <button type="button" class="btn btn-danger btn-sm removerPorta" data-porta="${i}">
                            <i class="fa-solid fa-trash-can"></i>
                        </button>
                    </td>
                </tr>
            `);
            $(`.rolo[data-porta="${i}"]`).val("0.60");
            $("#accordionProdutos").append(criarAcordeonProdutos(i));
            $("#accordionAdicionais").append(criarAcordeonAdicionais(i));
            recalcularTotaisPorta(i);
        }
    }
    $(document).on(
        'focus',
        '.larg, .alt, .id_larg, .larg-corte, .alt-corte, .qtd-laminas, ' +
        '.m2, .ft-peso, .peso, .qtd-prod-adc, .qtd-prod, .valor-prod, .valor-prod-adc',
        function () {
            if (!$(this).data('mask-applied')) {
                $(this)
                    .mask('00000.00', { reverse: true })
                    .data('mask-applied', true);
            }
        }
    );

    function criarFormularioProduto(num) {
        return `
        <div class="row g-2 mb-3 form-produto" data-porta="${num}">

            <div class="col-md-2">
                <label class="form-label">Cód. Produto</label>
                <div class="input-group">
                    <input type="text"
                        class="form-control form-control-sm cod-prod"
                        data-porta="${num}"
                        name="cod-prod"
                        placeholder="Cód. Produto">
                    <button class="btn btn-outline-dark btn-sm btn-busca-prod"
                            data-porta="${num}">
                        🔎
                    </button>
                </div>
            </div>

            <div class="col-md-3">
                <label class="form-label">Descrição</label>
                <input type="text"
                    class="form-control form-control-sm desc-prod"
                    data-porta="${num}"
                    name="desc-prod"
                    disabled>
            </div>

            <div class="col-md-1">
                <label class="form-label">Unidade</label>
                <input type="text"
                    class="form-control form-control-sm unid-prod"
                    data-porta="${num}"
                    name="unid-prod"
                    disabled>
            </div>

            <div class="col-md-2">
                <label class="form-label">Valor</label>
                <input type="text"
                    class="form-control form-control-sm valor-prod text-end"
                    name="valor-prod"
                    value="0.00"
                    style='color: darkgreen; font-weight: bold; background: honeydew;'
                    data-porta="${num}">
            </div>

            <div class="col-md-2">
                <label class="form-label">Qtde.</label>
                <input type="text"
                    class="form-control form-control-sm qtd-prod"
                    name="qtd-prod"
                    placeholder="0.00"
                    value="0.00"
                    data-porta="${num}">
            </div>

            <div class="col-md-2 d-flex align-items-end">
                <button type="button"
                        class="btn btn-success btn-sm btn-add-prod"
                        data-porta="${num}">
                    <i class="fas fa-plus"></i> Incluir
                </button>
            </div>

        </div>
        `;
    }

    function criarAcordeonProdutos(num) {
        return `
        <div class="accordion-item acc-produto porta-${num}" id="accProd_${num}" data-porta="${num}">
            <h2 class="accordion-header" id="headingProd_${num}">
                <button class="accordion-button collapsed fw-bold" type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#collapseProd_${num}">
                    Produtos – Porta ${num}
                </button>
            </h2>
            <div id="collapseProd_${num}" class="accordion-collapse collapse">
                <div class="accordion-body table-container w-100">
                    <!-- 🔥 FORMULÁRIO DO PRODUTO -->
                    ${criarFormularioProduto(num)}
                    <table class="table table-bordered table-sm table-striped tabela-produtos"
                        id="tblProd_${num}">
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
                                <th style="width: 70px;">Ações</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                    <!-- 🔥 Totais da porta -->
                    <div class="d-flex justify-content-end gap-4 mt-2 porta-totais"
                        data-porta="${num}">
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
        </div>`;
    }
    function criarFormularioAdicional(num) {
        return `
        <div class="row g-2 mb-3 form-adicional" data-porta="${num}">

            <div class="col-md-2">
                <label class="form-label">Cód. Produto</label>
                <div class="input-group">
                    <input type="text"
                        class="form-control form-control-sm cod-prod-adc"
                        name="cod-prod-adc"
                        data-porta="${num}"
                        placeholder="Cód. Produto">
                    <button class="btn btn-outline-dark btn-sm btn-busca-prod-adc"
                            data-porta="${num}">
                        🔎
                    </button>
                </div>
            </div>

            <div class="col-md-3">
                <label class="form-label">Descrição</label>
                <input type="text"
                    class="form-control form-control-sm desc-prod-adc"
                    name="desc-prod-adc"
                    data-porta="${num}"
                    disabled>
            </div>

            <div class="col-md-1">
                <label class="form-label">Unidade</label>
                <input type="text"
                    class="form-control form-control-sm unid-prod-adc"
                    name="unid-prod-adc"
                    data-porta="${num}"
                    disabled>
            </div>

            <div class="col-md-2">
                <label class="form-label">Valor</label>
                <input type="text"
                    class="form-control form-control-sm valor-prod-adc text-end"
                    name="valor-prod-adc"
                    value="0.00"
                    style='color: darkgreen; font-weight: bold; background: honeydew;'
                    data-porta="${num}">
            </div>

            <div class="col-md-2">
                <label class="form-label">Qtde.</label>
                <input type="text"
                    class="form-control form-control-sm qtd-prod-adc"
                    placeholder="0.00"
                    value="0.00"
                    name="qtd-prod-adc"
                    data-porta="${num}">
            </div>

            <div class="col-md-2 d-flex align-items-end">
                <button type="button"
                        class="btn btn-success btn-sm btn-add-prod-adc"
                        data-porta="${num}">
                    <i class="fas fa-plus"></i> Incluir
                </button>
            </div>

        </div>
        `;
    }
    function criarAcordeonAdicionais(num) {
        return `
        <div class="accordion-item acc-adicional porta-${num}" id="accAdc_${num}" data-porta="${num}">
            <h2 class="accordion-header" id="headingAdc_${num}">
                <button class="accordion-button collapsed fw-bold" type="button"
                    data-bs-toggle="collapse"
                    data-bs-target="#collapseAdc_${num}">
                    Adicionais – Porta ${num}
                </button>
            </h2>
            <div id="collapseAdc_${num}" class="accordion-collapse collapse">
                <div class="accordion-body table-container w-100">
                    ${criarFormularioAdicional(num)}
                    <table class="table table-bordered table-sm table-striped tabela-adicionais"
                        id="tblAdc_${num}">
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
                                <th style="width: 70px;">Ações</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                    <!-- 🔥 Totais dos adicionais por porta -->
                    <div class="d-flex justify-content-end gap-4 mt-2 porta-totais"
                        data-porta="${num}">
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
        </div>`;
    }
    function adicionarProdutoNaTabela(porta, dados) {
        const p = Number(porta);

        if (!prodManager.data[p]) {
            prodManager.data[p] = [];
        }

        let item = prodManager.data[p]
            .find(x => Number(x.cod) === Number(dados.cod));

        if (!item) {
            item = {
                id: Number(dados.cod),               // 🔒 id REAL
                cod: Number(dados.cod),
                desc: dados.desc,
                unid: dados.unid,
                vl_compra: 0,
                vl_unit: parseFloat(dados.vl) || 0,

                qtd_calc: 0,
                qtd_final: 0,
                qtd_manual: true,             // 🔒 NASCE MANUAL
                ativo: true
            };

            prodManager.data[p].push(item);
        }

        // 🔒 SEMPRE qtd_final
        item.qtd_final  = parseFloat(dados.qtd) || 0;
        item.qtd_manual = true;
        item.ativo      = item.qtd_final > 0;
        item.vl_unit    = parseFloat(dados.vl) || 0;

        let $row = $(`#tblProd_${p} tbody tr[data-item-id="${item.cod}"]`);


        if (!$row.length) {
            $row = $(`
                <tr data-porta="${p}" data-item-id="${item.cod}">
                    <td data-label="Código:" class="td-cod mobile-full">${item.cod}</td>
                    <td data-label="Descrição:" class="td-desc mobile-full">${dados.desc || item.desc}</td>
                    <td data-label="Unidade:" class="td-unid mobile-full">${item.unid}</td>
                    <td class="td-vl-compra text-danger fw-bold mobile-full" data-label="Vl. Compra:">0.00</td>
                    <td class="vl-unit text-success fw-bold mobile-full" data-label="Vl. Unit:">0.00</td>
                    <td class="qtd-produto mobile-full" data-label="Quantidade:">0.00</td>
                    <td class="tot-compra text-danger fw-bold mobile-full" data-label="Tot. Compra:">0.00</td>
                    <td class="vl-total text-success fw-bold mobile-full" data-label="Vl. Total:">0.00</td>
                    <td data-label="Ações:" class="mobile-full">
                        <i class="fas fa-edit editBtn" style="color: #13c43f; cursor: pointer;" data-bs-toggle="modal" data-bs-target="#editItemModal"></i>
                        <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor: pointer;"></i>
                    </td>
                </tr>
            `);

            $(`#tblProd_${p} tbody`).append($row);
        }
        /* 🔒 SINCRONIZA VISUAL */
        $row.find('.vl-unit')
            .text(item.vl_unit.toFixed(2));

        $row.find('.qtd-produto')
            .text(item.qtd_final.toFixed(2));
        const totCompra = item.qtd_final * item.vl_compra;
        const vlTotal   = item.qtd_final * item.vl_unit;
        $row.find('.tot-compra')
            .text(totCompra.toFixed(2));

        $row.find('.vl-total')
            .text(vlTotal.toFixed(2));
        atualizarTabelaPorta(p);
        atualizarSubtotal();
        atualizarJSONPortas();
    }
    function adicionarAdicionalNaTabela(porta, dados) {
        const p = Number(porta);

        if (!prodAdcManager.data[p]) {
            prodAdcManager.data[p] = [];
        }

        let item = prodAdcManager.data[p]
            .find(x => Number(x.cod) === Number(dados.cod));

        if (!item) {
            item = {
                id: Number(dados.cod),   
                cod: Number(dados.cod),
                desc: dados.desc,
                unid: dados.unid,
                vl_compra: 0,
                vl_unit: parseFloat(dados.vl) || 0,

                qtd_calc: 0,
                qtd_final: 0,
                qtd_manual: true,             // 🔒 NASCE MANUAL
                ativo: true
            };

            prodAdcManager.data[p].push(item);
        }

        // 🔒 SEMPRE qtd_final
        item.qtd_final  = parseFloat(dados.qtd) || 0;
        item.qtd_manual = true;
        item.ativo      = item.qtd_final > 0;
        item.vl_unit    = parseFloat(dados.vl) || 0;

        let $row = $(`#tblAdc_${p} tbody tr[data-item-id="${item.cod}"]`);

        if (!$row.length) {
            $row = $(`
                <tr data-porta="${p}" data-item-id="${item.cod}">
                    <td data-label="Código:" class="td-cod mobile-full">${item.cod}</td>
                    <td data-label="Descrição:" class="td-desc mobile-full">${dados.desc || item.desc}</td>
                    <td data-label="Unidade:" class="td-unid mobile-full">${item.unid}</td>
                    <td class="td-vl-compra text-danger fw-bold mobile-full" data-label="Vl. Compra:">0.00</td>
                    <td class="vl-unit text-success fw-bold mobile-full" data-label="Vl. Unit:">0.00</td>
                    <td class="qtd-produto mobile-full" data-label="Quantidade:">0.00</td>
                    <td class="tot-compra text-danger fw-bold mobile-full" data-label="Tot. Compra:">0.00</td>
                    <td class="vl-total text-success fw-bold mobile-full" data-label="Vl. Total:">0.00</td>
                    <td data-label="Ações:" class="mobile-full">
                        <i class="fas fa-edit editBtn" style="color: #13c43f; cursor: pointer;" data-bs-toggle="modal" data-bs-target="#editItemAdcModal"></i>
                        <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor: pointer;"></i>
                    </td>
                </tr>
            `);

            $(`#tblAdc_${p} tbody`).append($row);
        }
        /* 🔒 SINCRONIZA VISUAL */
        $row.find('.vl-unit')
            .text(item.vl_unit.toFixed(2));

        $row.find('.qtd-produto')
            .text(item.qtd_final.toFixed(2));
        const totCompra = item.qtd_final * item.vl_compra;
        const vlTotal   = item.qtd_final * item.vl_unit;
        $row.find('.tot-compra')
            .text(totCompra.toFixed(2));

        $row.find('.vl-total')
            .text(vlTotal.toFixed(2));
        atualizarTabelaPorta(p);
        atualizarSubtotal();
        atualizarJSONPortas();
    }
    $(document).on("click", ".btn-add-prod", function () {
        const porta = $(this).data("porta");
        const cod  = $(`.cod-prod[data-porta="${porta}"]`).val();
        const desc = $(`.desc-prod[data-porta="${porta}"]`).val();
        const unid = $(`.unid-prod[data-porta="${porta}"]`).val();
        const qtd  = parseFloat(
            $(`.qtd-prod[data-porta="${porta}"]`).val().replace(',', '.')
        ) || 0;
        const vl   = parseFloat(
            $(`.valor-prod[data-porta="${porta}"]`).val().replace(',', '.')
        ) || 0;

        if (!cod || !desc || qtd <= 0) {
            alert('Produto principal incompleto');
            return;
        }

        adicionarProdutoNaTabela(porta, { cod, desc, unid, qtd, vl });
        $('.cod-prod, .desc-prod, .unid-prod, .valor-prod, .qtd-prod').val('');
        $('.cod-prod').focus();
    });
    $(document).on("click", ".btn-add-prod-adc", function () {
        const porta = $(this).data("porta");
        const cod  = $(`.cod-prod-adc[data-porta="${porta}"]`).val();
        const desc = $(`.desc-prod-adc[data-porta="${porta}"]`).val();
        const unid = $(`.unid-prod-adc[data-porta="${porta}"]`).val();
        const qtd = parseFloat(
            $(`.qtd-prod-adc[data-porta="${porta}"]`).val().replace(',', '.')
        ) || 0;
        const vl = parseFloat(
            $(`.valor-prod-adc[data-porta="${porta}"]`).val().replace(',', '.')
        ) || 0;
        if (!cod || !desc || qtd <= 0) {
            alert('Produto adicional incompleto');
            return;
        }
        adicionarAdicionalNaTabela(porta, {
            cod,
            desc,
            unid,
            qtd,
            vl
        });
        $(`.cod-prod-adc[data-porta="${porta}"],
        .desc-prod-adc[data-porta="${porta}"],
        .unid-prod-adc[data-porta="${porta}"],
        .valor-prod-adc[data-porta="${porta}"],
        .qtd-prod-adc[data-porta="${porta}"]`).val('');
        $(`.cod-prod-adc[data-porta="${porta}"]`).focus();
    });
    function formatarBR(valor) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(valor);
    }
    function recalcularTotaisPorta(porta) {
        let totalCompra = 0;
        let totalVenda = 0;
        let totalCompraAdc = 0;
        let totalVendaAdc = 0;
        // Produtos
        $("#tblProd_" + porta + " tbody tr").each(function () {
            const compra = parseFloat(
                $(this).find(".tot-compra").text().replace(",", ".")
            ) || 0;
            const venda = parseFloat(
                $(this).find(".vl-total").text().replace(",", ".")
            ) || 0;
            totalCompra += compra;
            totalVenda += venda;
        });
        // Adicionais
        $("#tblAdc_" + porta + " tbody tr").each(function () {
            const compra = parseFloat(
                $(this).find(".tot-compra").text().replace(",", ".")
            ) || 0;
            const venda = parseFloat(
                $(this).find(".vl-total").text().replace(",", ".")
            ) || 0;
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
    // function aplicarRegraLaminaTipo(porta) {
    //     const tipoSelecionado = $("#id_lamina_tipo").val();
    //     if (!tipoSelecionado) return;

    //     const regra = {
    //         "Fechada": "LÂMINAS LISAS",
    //         "Transvision": "LÂMINAS TRANSVISION"
    //     };

    //     const descPermitida = regra[tipoSelecionado];
    //     if (!descPermitida) return;

    //     prodManager.data[porta].forEach(item => {
    //         if (!item.desc?.toUpperCase().includes("LÂMINAS")) return;

    //         if (item.desc.toUpperCase() === descPermitida.toUpperCase()) {
    //             item.ativo = true;
    //         } else {
    //             item.ativo = false;
    //             item.qtd_calc = 0;
    //             item.qtd_final = 0;

    //             $(`#tblProd_${porta} tbody tr[data-item-id="${item.id}"]`).remove();
    //         }
    //     });
    // }
    function reposicionarMotor(porta) {
        const $tbody = $(`#tblProd_${porta} tbody`);

        const $motorRow = $tbody.find("tr").filter(function () {
            return $(this).find(".td-desc").text().toUpperCase().includes("MOTOR");
        });

        if ($motorRow.length) {
            $motorRow.detach().appendTo($tbody);
        }
    }
    function reposicionarLaminaPrimeiro(porta) {

        const $tbody = $(`#tblProd_${porta} tbody`);

        const $laminaRow = $tbody.find("tr").filter(function () {
            return $(this)
                .find(".td-desc")
                .text()
                .toUpperCase()
                .includes("LÂMINAS");
        });

        if ($laminaRow.length) {
            $laminaRow.detach().prependTo($tbody);
        }
    }
    $(document).on("blur", ".larg, .alt", async function () {
        const porta = $(this).data("porta");
        const lg = parseFloat($(`.larg[data-porta="${porta}"]`).val().replace(",", ".")) || 0;
        const at = parseFloat($(`.alt[data-porta="${porta}"]`).val().replace(",", ".")) || 0;
        if (lg <= 0 || at <= 0) return;
        medidasCtrl[porta] ??= {};
        const ctrl = medidasCtrl[porta];
        const mudouMedida = ctrl.larg !== lg || ctrl.alt !== at;
        if (!mudouMedida) {
            atualizarSubtotal();
            return;
        }
        ctrl.larg = lg;
        ctrl.alt  = at;
        iniciarLoading();
        calcM2(porta);
        calcFtPeso(porta);
        calcLgCorte(porta);
        calcPeso(porta);
        calcularEixoMotor(porta);
        calcQtdLam(porta);
        await buscarProdutosPrincipais(porta, lg, at);
        await buscarProdutosAdicionais(porta);
        await buscarMotorIdeal(porta);
        atualizarTabelaPorta(porta);
        atualizarLaminarPorta(porta);
        reposicionarMotor(porta);
        reposicionarLaminaPrimeiro(porta);
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
        const cod   = Number($tr.data('item-id'));

        const lista = prodAdcManager.data[porta];
        if (!lista) return;

        const item = lista.find(x => Number(x.cod) === cod);
        if (item) {
            item.ativo = false;     // 🔒 desativa de verdade
            item.qtd_final = 0;
        }

        $tr.remove();

        recalcularTotaisPorta(porta);
        atualizarSubtotal();
        atualizarJSONPortas();
    });

    function resetarPorta(porta) {
        // limpa memória de produtos
        if (window.prodManager?.data) {
            prodManager.data[porta] = [];
        }
        if (window.prodAdcManager?.data) {
            prodAdcManager.data[porta] = [];
        }

        // limpa tabelas se existirem
        $(`#tblProd_${porta} tbody`).empty();
        $(`#tblAdc_${porta} tbody`).empty();
    }

    function reindexarPortas() {
        let novoIndice = 1;
        $("#tabelaPortasResumo tbody tr").each(function () {
            $(this).attr("id", "linha_resumo_" + novoIndice);
            $(this).find(".num-porta").text(novoIndice);
            $(this).find("input, select").each(function () {
                $(this).attr("data-porta", novoIndice);
            });
            $(this).find(".removerPorta").attr("data-porta", novoIndice);
            novoIndice++;
        });
        novoIndice = 1;
        $("#accordionProdutos .acc-produto").each(function () {
            $(this).attr("id", "accProd_" + novoIndice);
            $(this).attr("data-porta", novoIndice);
            $(this).find(".accordion-header").attr("id", "headingProd_" + novoIndice);
            $(this).find(".accordion-button")
                .attr("data-bs-target", "#collapseProd_" + novoIndice)
                .text("Produtos – Porta " + novoIndice);
            $(this).find(".accordion-collapse").attr("id", "collapseProd_" + novoIndice);
            $(this).find(".tabela-produtos").attr("id", "tblProd_" + novoIndice);
            novoIndice++;
        });
        novoIndice = 1;
        $("#accordionAdicionais .acc-adicional").each(function () {
            $(this).attr("id", "accAdc_" + novoIndice);
            $(this).attr("data-porta", novoIndice);
            $(this).find(".accordion-header").attr("id", "headingAdc_" + novoIndice);
            $(this).find(".accordion-button")
                .attr("data-bs-target", "#collapseAdc_" + novoIndice)
                .text("Adicionais – Porta " + novoIndice);
            $(this).find(".accordion-collapse").attr("id", "collapseAdc_" + novoIndice);
            $(this).find(".tabela-adicionais").attr("id", "tblAdc_" + novoIndice);
            novoIndice++;
        });
        $("#qtd_portas").val($("#tabelaPortasResumo tbody tr").length);
        if (typeof atualizarJSONPortas === "function") {
            atualizarJSONPortas();
        }
    }
    let REGRAS = {};
    function carregarRegras() {
        return $.getJSON('/regras_produto/js/', function (data) {
            REGRAS = data;
            console.log('Regras carregadas:', REGRAS);
        });
    }
    carregarRegras();
    function calcularQtdPorRegra(item, ctx) {

        if (!item.regra || item.regra.tipo !== 'QTD')
            return Number(item.qtd) || 0;

        const { alt, alt_c, larg, larg_c, m2 } = ctx;
        let qtd = 0;

        switch (item.regra.codigo) {
            case 'GUIAS_ALTURA':
            case 'TUBO_AFASTAMENTO':
                qtd = (alt_c + 0.2) * 2;
                break;
            case 'EIXO_LARGURA':
            case 'SOLEIRA_LARGURA':
                qtd = larg_c;
                break;
            case 'PERFIL_DESLIZANTE':
                qtd = alt_c * 4;
                break;
            case 'TRAVA_LAMINA':
                qtd = alt * 10;
                break;
            case 'LAMINAS_M2':
                qtd = m2;
                break;
            case 'MOTOR_UNIDADE':
            case 'TRANSPORTE_UNIDADE':
            case 'MAO_OBRA_UNIDADE':
                qtd = 1;
                break;
            case 'QTD_PADRAO_ZERO':
            default:
                qtd = 0;
        }

        return Number(qtd) || 0;
    }

    function atualizarTabelaPorta(porta) {
        console.log('>>> atualizarTabelaPorta CHAMADA:', porta);
        const tp_pintura = $('#id_tp_pintura').val();
        const ctrl = medidasCtrl[porta] || {};

        const larg   = Number(ctrl.larg)   || 0;
        const alt    = Number(ctrl.alt)    || 0;
        const larg_c = parseFloat($(`.larg-corte[data-porta="${porta}"]`).val()) || 0;
        const alt_c  = parseFloat($(`.alt-corte[data-porta="${porta}"]`).val()) || 0;
        const m2     = parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;

        let totalCompraProd = 0;
        let totalVendaProd  = 0;
        let totalCompraAdc  = 0;
        let totalVendaAdc   = 0;
        console.log(
            'TR PROD:',
            $(`#tblProd_${porta} tbody tr`).length,
            'TR ADC:',
            $(`#tblAdc_${porta} tbody tr`).length
        );

        $(`#tblProd_${porta} tbody tr`).each(function () {
            const $tr = $(this);
            const itemId = Number($tr.data('item-id'));
            const item = prodManager.data[porta]?.find(i => i.id === itemId);
            if (!item) return;
            if (item.vl_compra == null) {
                const txt = $tr.find('.td-vl-compra').text().trim().replace(',', '.');
                item.vl_compra = Number(txt) || 0;
            }
            if (item.vl_unit == null) {
                const txtVenda = $tr.find('.vl-unit').text().trim().replace(',', '.');
                item.vl_unit = Number(txtVenda) || 0;
            }
            item.vl_compra = Number(item.vl_compra) || 0;
            item.vl_unit   = Number(item.vl_unit)   || 0;
            item.qtd_calc  ??= 0;
            item.qtd_final ??= 0;

            if (item.ativo === false) {
                $tr.hide();
                return;
            }

            const qtdCalc = calcularQtdPorRegra(item, { alt, alt_c, larg, larg_c, m2 });
            item.qtd_calc = qtdCalc;

            if (!item.qtd_manual) {
                item.qtd_final = qtdCalc;
            } else {
                item.qtd_final = Number(item.qtd_final) || 0;
            }

            if (item.qtd_final <= 0) {
                item.ativo = false;
                $tr.hide();
                return;
            }

            item.ativo = true;
            $tr.show();

            const totCompra = item.vl_compra * item.qtd_final;
            const totVenda  = item.vl_unit   * item.qtd_final;

            console.log('DEBUG CALC:', {
                cod: item.cod,
                qtd: item.qtd_final,
                vl_compra: item.vl_compra,
                vl_unit: item.vl_unit,
                compra_calc: totCompra,
                venda_calc: totVenda
            });

            $tr.find('.qtd-produto').text(item.qtd_final.toFixed(2));
            $tr.find('.tot-compra').text(totCompra.toFixed(2));
            $tr.find('.vl-total').text(totVenda.toFixed(2));

            totalCompraProd += totCompra;
            totalVendaProd  += totVenda;
        });

        $(`#tblAdc_${porta} tbody tr`).each(function () {
            const $tr = $(this);
            const itemId = Number($tr.data('item-id'));
            const item = prodAdcManager.data[porta]?.find(i => i.id === itemId);
            if (!item) return;
            // 🚫 bloqueia pintura se estiver "Não"
            if (
                $('#id_pintura').val() === 'Não' &&
                item.regra_origem === 'PINTURA_TIPO'
            ) {
                item.ativo = false;
                item.qtd_calc = 0;
                item.qtd_final = 0;
                $tr.hide();
                return;
            }

            if (item.vl_compra == null) {
                const txt = $tr.find('.td-vl-compra').text().trim().replace(',', '.');
                item.vl_compra = Number(txt) || 0;
            }
            if (item.vl_unit == null) {
                const txtVenda = $tr.find('.vl-unit').text().trim().replace(',', '.');
                item.vl_unit = Number(txtVenda) || 0;
            }
            item.vl_compra = Number(item.vl_compra) || 0;
            item.vl_unit   = Number(item.vl_unit)   || 0;
            item.qtd_calc  ??= 0;
            item.qtd_final ??= 0;

            if (item.ativo === false) {
                $tr.hide();
                return;
            }

            let qtdCalc = 0;

            if (
                item.regra?.codigo === 'PINTURA_M2' &&
                (
                    (tp_pintura === 'Eletrostática' && item.desc.includes('ELETROSTÁTICA')) ||
                    (tp_pintura === 'Automotiva'     && item.desc.includes('AUTOMOTIVA'))
                )
            ) {
                qtdCalc = m2;
            } else {
                qtdCalc = calcularQtdPorRegra(item, { alt, alt_c, larg, larg_c, m2 });
            }

            item.qtd_calc = qtdCalc;

            if (!item.qtd_manual) {
                item.qtd_final = qtdCalc;
            } else {
                item.qtd_final = Number(item.qtd_final) || 0;
            }

            if (item.qtd_final <= 0) {
                item.ativo = false;
                $tr.hide();
                return;
            }

            item.ativo = true;
            $tr.show();

            const totCompra = item.vl_compra * item.qtd_final;
            const totVenda  = item.vl_unit   * item.qtd_final;

            $tr.find('.qtd-produto').text(item.qtd_final.toFixed(2));
            $tr.find('.tot-compra').text(totCompra.toFixed(2));
            $tr.find('.vl-total').text(totVenda.toFixed(2));

            totalCompraAdc += totCompra;
            totalVendaAdc  += totVenda;
        });

        $(`#totCompra_porta_${porta}`).text("R$ " + totalCompraProd.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $(`#totVenda_porta_${porta}`).text("R$ " + totalVendaProd.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $(`#totCompraAdc_porta_${porta}`).text("R$ " + totalCompraAdc.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $(`#totVendaAdc_porta_${porta}`).text("R$ " + totalVendaAdc.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
    }

    function getDescricaoLaminaAtiva(porta) {
        const regra = REGRAS.LAMINA_TIPO;
        if (!regra || regra.tipo !== 'SELECAO') return null;

        const mapa = JSON.parse(regra.expressao);
        const valor = $(`.tipo-lamina[data-porta="${porta}"]`).val();

        return mapa[valor]?.toUpperCase().trim() || null;
    }
    function getDescricaoPinturaAtiva(porta) {
        const regra = REGRAS.PINTURA_TIPO;
        if (!regra || regra.tipo !== 'SELECAO') return null;

        const mapa = JSON.parse(regra.expressao);
        const valor = $('#id_tp_pintura').val();

        return mapa[valor]?.toUpperCase().trim() || null;
    }

    medidasCtrl = [];
    function buscarProdutosPrincipais(num, lg, at) {
        return new Promise((resolve) => {

            const p = Number(num);
            prodManager.data[p] ??= [];

            prodManager.data[p] = prodManager.data[p].filter(i =>
                i.desc?.toUpperCase().includes("MOTOR")
            );

            const $tbody = $("#tblProd_" + num + " tbody");

            $tbody.find("tr").each(function () {
                const desc = $(this).find(".td-desc").text().toUpperCase();
                if (!desc.includes("MOTOR")) {
                    $(this).remove();
                }
            });

            $.get('/produtos/lista_ajax/', {
                tp: "desc",
                tp_prod: "Principal"
            }, function (resp) {
                const laminaAtiva = getDescricaoLaminaAtiva(num);
                console.log('TIPO LÂMINA:', $(`.tipo-lamina[data-porta="${num}"]`).val());
                console.log('MAPA:', JSON.parse(REGRAS.LAMINA_TIPO.expressao));
                console.log('LAMINA ATIVA:', laminaAtiva);      
                resp.produtos.forEach(pdt => {

                    const desc = pdt.desc_prod.toUpperCase().trim();
                    if (desc.includes("MOTOR")) return;
                    // 🔒 SELEÇÃO DE LÂMINA VIA JS
                    if (desc.includes("LÂMINAS")) {
                        if (!laminaAtiva) return;
                        if (desc !== laminaAtiva) return;
                    }

                    prodManager.data[p].push({
                        id: pdt.id,
                        cod: pdt.id,
                        desc: pdt.desc_prod,
                        unid: pdt.unidProd,
                        vl_compra: parseFloat(pdt.vl_compra),
                        vl_unit: parseFloat(pdt.vl_prod),
                        qtd_calc: 0,
                        qtd_final: 0,
                        qtd_manual: false,
                        regra: pdt.regra,
                        // 🚫 lâmina SEMPRE nasce desativada
                        ativo: true
                    });

                    $tbody.append(`
                        <tr data-porta="${num}" data-item-id="${pdt.id}">
                            <td data-label="Código:" class="td-cod mobile-full">${pdt.id}</td>
                            <td data-label="Descrição:" class="td-desc mobile-full">${pdt.desc_prod}</td>
                            <td data-label="Unidade:" class="td-unid mobile-full">${pdt.unidProd}</td>
                            <td class="td-vl-compra text-danger fw-bold mobile-full" data-label="Vl. Compra:">${pdt.vl_compra}</td>
                            <td class="vl-unit text-success fw-bold mobile-full" data-label="Vl. Unit:">${pdt.vl_prod}</td>
                            <td class="qtd-produto mobile-full" data-label="Quantidade:">0.00</td>
                            <td class="tot-compra text-danger fw-bold mobile-full" data-label="Tot. Compra:">0.00</td>
                            <td class="vl-total text-success fw-bold mobile-full" data-label="Vl. Total:">0.00</td>
                            <td data-label="Ações:" class="mobile-full">
                                <i class="fas fa-edit editBtn" data-bs-toggle="modal"
                                data-bs-target="#editItemModal"
                                style="color: #13c43f; cursor: pointer;"></i>
                                <i class="fas fa-trash deleteBtn"
                                style="color: #db1e47; cursor: pointer;"></i>
                            </td>
                        </tr>
                        
                    `);
                });

                resolve(); // 🔔 AVISA: terminou
            });
        });
    }
    async function buscarProdutosAdicionais(porta) {
        const p = Number(porta);

        if (!prodAdcManager.data[p]) {
            prodAdcManager.data[p] = [];
        }

        return new Promise((resolve, reject) => {

            $.get('/produtos/lista_ajax/', {
                tp: "desc",
                tp_prod: "Adicional"
            })
            .done(function (resp) {

                const temPintura   = $('#id_pintura').val(); // Sim / Não
                const pinturaAtiva = getDescricaoPinturaAtiva(porta);

                const mapaPinturas = Object.values(
                    obterMapaSelecao(REGRAS.PINTURA_TIPO)
                ).map(d => d.toUpperCase().trim());

                /* ======================================================
                🚫 REMOVE ABSOLUTAMENTE PINTURA SE FOR "NÃO"
                ====================================================== */
                if (temPintura === 'Não') {
                    prodAdcManager.data[p] = prodAdcManager.data[p].filter(
                        item => item.regra_origem !== 'PINTURA_TIPO'
                    );
                }

                const tabela = $(`#tblAdc_${porta} tbody`).empty();

                resp.produtos.forEach(item => {
                    const desc = item.desc_prod.toUpperCase().trim();
                    const isPintura = mapaPinturas.includes(desc);

                    /* ======================================================
                    🔒 CONTROLE DE PINTURA
                    ====================================================== */
                    if (isPintura) {
                        if (temPintura === 'Não') return;
                        if (!pinturaAtiva || desc !== pinturaAtiva) return;
                    }

                    const existente = prodAdcManager.data[p]
                        .find(x => Number(x.cod) === Number(item.id));

                    const qtdInicial = existente
                        ? Number(existente.qtd_final ?? 0)
                        : 0;

                    if (!existente) {
                        prodAdcManager.data[p].push({
                            id: item.id,
                            cod: item.id,
                            desc: item.desc_prod,
                            unid: item.unidProd,
                            vl_compra: Number(item.vl_compra) || 0,
                            vl_unit: Number(item.vl_prod) || 0,
                            qtd_calc: qtdInicial,
                            qtd_final: qtdInicial,
                            qtd_manual: false,
                            regra: item.regra,
                            ativo: true,
                            regra_origem: isPintura ? 'PINTURA_TIPO' : null
                        });
                    } else {
                        existente.desc = item.desc_prod;
                        existente.unid = item.unidProd;
                        existente.vl_compra = Number(item.vl_compra) || 0;
                        existente.vl_unit = Number(item.vl_prod) || 0;
                        existente.regra = item.regra;
                        existente.ativo = true;
                    }

                    tabela.append(`
                        <tr data-porta="${porta}" data-item-id="${item.id}">
                            <td class="td-cod mobile-full">${item.id}</td>
                            <td class="td-desc mobile-full">${item.desc_prod}</td>
                            <td class="td-unid mobile-full">${item.unidProd}</td>
                            <td class="td-vl-compra text-danger fw-bold mobile-full">${item.vl_compra}</td>
                            <td class="vl-unit text-success fw-bold mobile-full">${item.vl_prod}</td>
                            <td class="qtd-produto mobile-full">${qtdInicial.toFixed(2)}</td>
                            <td class="tot-compra text-danger fw-bold mobile-full">0.00</td>
                            <td class="vl-total text-success fw-bold mobile-full">0.00</td>
                            <td class="mobile-full">
                                <i class="fas fa-edit editBtn" data-bs-toggle="modal"
                                data-bs-target="#editItemAdcModal"
                                style="color:#13c43f;cursor:pointer"></i>
                                <i class="fas fa-trash deleteBtn"
                                style="color:#db1e47;cursor:pointer"></i>
                            </td>
                        </tr>
                    `);
                });

                atualizarTabelaPorta(porta);
                atualizarSubtotal();
                atualizarJSONPortas();

                resolve();
            })
            .fail(err => reject(err));
        });
    }


    function hidratarAdicionaisDaTabelaSeVazio(porta) {
        const p = Number(porta);
        if (prodAdcManager.data[p] && prodAdcManager.data[p].length) {
            return;
        }
        prodAdcManager.data[p] = [];
        $(`#tblAdc_${p} tbody tr`).each(function () {
            const cod = $(this).find('.td-cod').text().trim();
            const qtd = parseFloat($(this).find('.qtd-produto').text()) || 0;
            if (cod) {
                prodAdcManager.data[p].push({
                    id: cod,
                    cod: cod,
                    qtd: qtd,
                    qtd_manual: false,
                    ativo: true
                });
            }
        });
    }
    function syncAdicionalFromTable(porta) {
        const p = Number(porta);
        if (!prodAdcManager.data[p]) {
            prodAdcManager.data[p] = [];
        }
        const mapa = {};
        prodAdcManager.data[p].forEach(item => {
            mapa[item.cod] = item;
        });
        $(`#tblAdc_${p} tbody tr`).each(function () {
            const cod = $(this).find('.td-cod').text().trim();
            const qtd = parseFloat($(this).find('.qtd-produto').text()) || 0;
            if (!cod) return;
            if (mapa[cod]) {
                mapa[cod].qtd = qtd;
            } else {
                prodAdcManager.data[p].push({
                    id: cod,
                    cod: cod,
                    qtd: qtd,
                    qtd_manual: false,
                    ativo: true
                });
            }
        });
    }
    $(".linha-porta").each(function () {
        const porta = $(this).data("porta");
        hidratarAdicionaisDaTabelaSeVazio(porta);
        atualizarJSONPortas();
    });
    function obterRegraProduto(codProd) {
        switch (codProd) {
            case 14: // EIXO
                return { tipo: 'QTD', codigo: 'EIXO_LARGURA' };

            case 15: // SOLEIRA
                return { tipo: 'QTD', codigo: 'SOLEIRA_LARGURA' };

            case 12:
                return { tipo: 'QTD', codigo: 'GUIAS_ALTURA' };

            case 13:
                return { tipo: 'QTD', codigo: 'TUBO_AFASTAMENTO' };

            case 16:
                return { tipo: 'QTD', codigo: 'PERFIL_DESLIZANTE' };

            case 17:
                return { tipo: 'QTD', codigo: 'TRAVA_LAMINA' };

            case 1:
                return { tipo: 'QTD', codigo: 'LAMINAS_M2' };

            case 3:
                return { tipo: 'QTD', codigo: 'MOTOR_UNIDADE' };

            default:
                return null;
        }
    }

    function hidratarManagersFromBackend() {
        let portas = getPortasFromBackend();
        if (!Array.isArray(portas) || portas.length === 0) {
            portas = [{
                numero: 1, largura: 0,
                altura: 0, qtd_lam: 0,
                m2: 0, larg_corte: 0,
                alt_corte: 0, rolo: 0,
                peso: 0, ft_peso: 0,
                eix_mot: 0, tipo_lamina: "", tipo_vao: "",
                produtos: [],
                adicionais: []
            }];
        }
        prodManager.data = {};
        prodAdcManager.data = {};
        const temPintura = $('#id_pintura').val(); // Sim / Não
        portas.forEach(porta => {
            const p = porta.numero;
            if (!p) return;
            prodManager.data[p] = [];
            prodAdcManager.data[p] = [];
            (porta.produtos || []).forEach(item => {
                const regra = obterRegraProduto(item.codProd);
                prodManager.data[p].push({
                    id: Number(item.codProd),
                    cod: Number(item.codProd),
                    regra: regra,
                    qtd_calc: Number(item.qtdProd),
                    qtd_final: Number(item.qtdProd),
                    qtd_manual: true,
                    ativo: item.ativo !== false,
                    // 🔥 NÃO inventa origem
                    regra_origem: item.regra_origem || null
                });

            });
            (porta.adicionais || []).forEach(item => {

                const produto = $(`#tblAdc_${p} tbody tr[data-item-id="${item.codProd}"]`);
                const regraOrigemDom = produto.data('regra-origem') || null;

                const isPintura = regraOrigemDom === 'PINTURA_TIPO';

                const ativo = !(isPintura && temPintura === 'Não');

                prodAdcManager.data[p].push({
                    id: Number(item.codProd),
                    cod: Number(item.codProd),
                    regra: null,
                    qtd_calc: Number(item.qtdProd),
                    qtd_final: ativo ? Number(item.qtdProd) : 0,
                    qtd_manual: true,
                    ativo: ativo,
                    regra_origem: isPintura ? 'PINTURA_TIPO' : null
                });
            });

            if (temPintura === 'Não') {
                $(`#tblAdc_${p} tbody tr`).each(function () {
                    const desc = $(this).find('.td-desc').text().toUpperCase().trim();
                    const mapaPinturas = Object.values(obterMapaSelecao(REGRAS.PINTURA_TIPO))
                        .map(d => d.toUpperCase().trim());
                    if (mapaPinturas.includes(desc)) {
                        $(this).remove();
                    }
                });
            }
        });
        console.log('Managers OK', prodManager.data, prodAdcManager.data);
        return portas;
    }
    function atualizarJSONPortas() {
        let portas = [];
        $('table[id^="tblProd_"]').each(function() {
            const tableId = $(this).attr('id'); // tblProd_1
            const p = tableId.split('_')[1];
            const mapaProdutos = new Map();

            (prodManager.data[p] || []).forEach(item => {
                if (!item.ativo || item.qtd_final <= 0) return;

                // 🔥 sempre sobrescreve → o último vence
                mapaProdutos.set(item.cod, {
                    codProd: Number(item.cod),
                    qtdProd: Number(item.qtd_final),
                    ativo: true
                });
            });

            const produtos = Array.from(mapaProdutos.values());



            const adicionais = [];
            const semPintura = $('#id_pintura').val() === 'Não';
            (prodAdcManager.data[p] || []).forEach(item => {
                if (
                    item.ativo &&
                    item.qtd_final > 0 &&
                    !(item.regra_origem === 'PINTURA_TIPO' && $('#id_pintura').val() === 'Não')
                ) {
                    adicionais.push({
                        codProd: Number(item.cod),
                        qtdProd: Number(item.qtd_final),
                        ativo: true
                    });
                }
            });
            portas.push({
                numero: Number(p),
                produtos,
                adicionais,
                largura: getFloat(`.larg[data-porta="${p}"]`),
                altura: getFloat(`.alt[data-porta="${p}"]`),
                qtd_lam: getFloat(`.qtd-laminas[data-porta="${p}"]`),
                m2: getFloat(`.m2[data-porta="${p}"]`),
                larg_corte: getFloat(`.larg-corte[data-porta="${p}"]`),
                alt_corte: getFloat(`.alt-corte[data-porta="${p}"]`),
                rolo: getFloat(`.rolo[data-porta="${p}"]`),
                peso: getFloat(`.peso[data-porta="${p}"]`),
                ft_peso: getFloat(`.ft-peso[data-porta="${p}"]`),
                eix_mot: getFloat(`.eix-mot[data-porta="${p}"]`),
                tipo_lamina: $(`.tipo-lamina[data-porta="${p}"]`).val() || "",
                tipo_vao: $(`.tipo-vao[data-porta="${p}"]`).val() || ""
            });
        });
        console.log("JSON FINAL:", portas);
        $("#id_json_portas").val(JSON.stringify(portas));
        return true;
    }

    function getFloat(selector) {
        const el = $(selector);
        if (!el.length) return 0;

        const val = el.val();
        if (!val) return 0;

        return parseFloat(val.replace(',', '.')) || 0;
    }
    function getSelect2IdIfExists(selector) {
        const $el = $(selector);

        // campo não existe neste formulário → ignora
        if ($el.length === 0) {
            return undefined;
        }

        const data = $el.select2('data') || [];
        return data.length ? data[0].id : null;
    }
    $('#openModalBtn').on('click', async function (e) {
        e.preventDefault();
        e.stopPropagation();

        await atualizarSubtotal();

        const temPintura = $("#id_pintura").val();
        const corSelecionada = $("#id_cor").val();

        const filial = getSelect2IdIfExists('#id_vinc_fil');
        const solicitante = getSelect2IdIfExists('#id_solicitante');
        const cliente = getSelect2IdIfExists('#id_cli');

        if (temPintura === "Sim" && (!corSelecionada || corSelecionada === "")) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Escolha uma cor da pintura antes de gravar!", cor_amarelo);
            $("#medidasBtn").click();
            return false;
        }

        // só valida se o campo existir
        if (filial !== undefined && !filial) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Filial deve ser informada!", cor_amarelo);
            $("#clienteBtn").click();
            return false;
        }

        if (solicitante !== undefined && !solicitante) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Solicitante deve ser informado!", cor_amarelo);
            $("#clienteBtn").click();
            return false;
        }

        if (cliente !== undefined && !cliente) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Cliente deve ser informado!", cor_amarelo);
            $("#clienteBtn").click();
            return false;
        }

        if (!verificarTotalFormas()) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Total das formas de pagamento não corresponde ao valor total!", cor_amarelo);
            return false;
        }

        $('#staticBackdrop').modal('show');
    });

    $(document).on("click", ".btn-faturar", function (e) {
        e.preventDefault();
        e.stopPropagation();
        const id = $(this).data("id");
        const faturarModal = new bootstrap.Modal(
            document.getElementById("faturarModal-" + id),
            { backdrop: 'static', keyboard: false }
        );
        faturarModal.show();
    });
    $(document).on("click", ".btn-confirmar-faturamento", function () {
        const id = $(this).data("id");
        const confirmModal = new bootstrap.Modal(
            document.getElementById("staticBackdrop" + id),
            { backdrop: 'static', keyboard: false }
        );
        confirmModal.show();
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
        zerarTotais();
        gerarPortas();
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
    });
    
    function aplicarRegraQuantidade(item, porta) {
        // ❌ NÃO recalcula se foi editado manualmente
        if (item.qtd_manual) {
            return item.qtd;
        }

        // ✅ Regra automática
        if (!item.regra) return item.qtd;

        switch (item.regra.tipo) {
            case 'M2':
                return parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;

            case 'ALTURA':
                return parseFloat($(`.alt[data-porta="${porta}"]`).val()) || 0;

            default:
                return item.qtd;
        }
    }
    function rebuildManagersFromBackend(portasJson) {

        prodManager.data = {};
        prodAdcManager.data = {};
        medidasCtrl = {};

        portasJson.forEach((p, idx) => {

            const porta = p.numero ?? idx;

            // 🔹 MEDIDAS
            medidasCtrl[porta] = {
                larg: p.largura,
                alt: p.altura,
                m2: p.m2,
                larg_c: p.larg_corte,
                alt_c: p.alt_corte,
                peso: p.peso,
                ft_peso: p.ft_peso,
                eix_mot: p.eix_mot
            };

            // 🔹 PRODUTOS
            prodManager.data[porta] = p.produtos.map(item => ({
                codProd: Number(item.codProd),
                qtdProd: Number(item.qtdProd),
                qtd_calc: Number(item.qtdProd),
                qtd_final: Number(item.qtdProd),
                qtd_manual: true,   // 🔐 veio do banco
                ativo: Number(item.qtdProd) > 0,
                regra: item.regra
            }));

            // 🔹 ADICIONAIS
            prodAdcManager.data[porta] = p.adicionais.map(item => ({
                codProd: Number(item.codProd),
                qtdProd: Number(item.qtdProd),
                qtd_calc: Number(item.qtdProd),
                qtd_final: Number(item.qtdProd),
                qtd_manual: true,
                ativo: Number(item.qtdProd) > 0,
                regra: item.regra
            }));
        });
    }
    if (typeof PORTAS_BACKEND !== "undefined" && PORTAS_BACKEND.length) {

        rebuildManagersFromBackend(PORTAS_BACKEND);

        PORTAS_BACKEND.forEach(p => {
            atualizarTabelaPorta(p.numero);
            reposicionarLaminaPrimeiro(p.numero);
            reposicionarMotor(p.numero);
        });

        atualizarSubtotal();
    }

    $('.modal').on('hidden.bs.modal', function () {
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open');
    });
    // Eventos comuns
    $(document).on('click', '.editBtn', function () {
        const $tr = $(this).closest('tr');
        const porta = Number($tr.data('porta'));
        const itemId = Number($tr.data('item-id'));
        const isProd = $(this).closest('table').is('#tblProd_' + porta);
        const isAdc  = $(this).closest('table').is('#tblAdc_' + porta);
        if (isProd) {
            prodManager.setEditingItem($tr);
            console.log('DEBUG EDIT:', {
                porta,
                itemId,
                dataPorta: prodManager.data[porta]
            });

            const item = prodManager.data[porta]?.find(i => i.id === itemId);
            console.log('UNIDADE ITEM:', item);

            if (!item) return;
            $('#editItemModal .modal-title').html(
                `<i class="fa-solid fa-pen-to-square"></i> Editar Item ${item.cod}`
            );
            const cod  = item.cod ?? $tr.find('.td-cod').text().trim();
            const desc = item.desc ?? $tr.find('.td-desc').text().trim();
            const unid = item.unid ?? $tr.find('.td-unid').text().trim();

            const vl =
                item.vl_unit ??
                item.vl_unitario ??
                parseFloat($tr.find('.vl-unit').text().replace(',', '.')) ??
                0;


            const qtd =
                item.qtd_final ??
                item.qtd ??
                parseFloat($tr.find('.qtd-produto').text().replace(',', '.')) ??
                0;

            $('#editCódInput').val(cod);
            $('#editDescInput').val(desc);
            $('#editUnidInput').val(unid);
            $('#editValorItemInput').val(Number(vl).toFixed(2));
            $('#editQtdInput').val(Number(qtd).toFixed(2));

            const modalEdit = new bootstrap.Modal(
                document.getElementById('editItemModal')
            );
            modalEdit.show();
        }
        else if (isAdc) {
            prodAdcManager.setEditingItem($tr);
            const item = prodAdcManager.data[porta]?.find(i => i.id === itemId);
            if (!item) return;
            $('#editItemAdcModal .modal-title').html(
                `<i class="fa-solid fa-pen-to-square"></i> Editar Item ${item.cod}`
            );
            const cod  = item.cod ?? $tr.find('.td-cod').text().trim();
            const desc = item.desc ?? $tr.find('.td-desc').text().trim();
            const unid = item.unid ?? $tr.find('.td-unid').text().trim();

            const vl =
                item.vl_unit ??
                item.vl_unitario ??
                parseFloat($tr.find('.vl-unit').text().replace(',', '.')) ??
                0;


            const qtd =
                item.qtd_final ??
                item.qtd ??
                parseFloat($tr.find('.qtd-produto').text().replace(',', '.')) ??
                0;

            $('#editCódAdcInput').val(cod);
            $('#editDescAdcInput').val(desc);
            $('#editUnidAdcInput').val(unid);
            $('#editValorItemAdcInput').val(Number(vl).toFixed(2));
            $('#editQtdAdcInput').val(Number(qtd).toFixed(2));
            const modalAdc = new bootstrap.Modal(
                document.getElementById('editItemAdcModal')
            );
            modalAdc.show();
        }
    });
    $('#saveEditBtn').on('click', function () {
        const { porta, itemId } = prodManager.currentEditing;
        if (!porta || !itemId) return;
        const cells = [
            $('#editCódInput').val().trim(),
            $('#editDescInput').val().trim(),
            $('#editUnidInput').val().trim(),
            $('#editValorItemInput').val().trim(),
            $('#editQtdInput').val().trim()
        ];
        prodManager.updateEditingItem(cells);
        bootstrap.Modal.getInstance(
            document.getElementById('editItemModal')
        ).hide();
        prodManager.clearEditing();
    });
    $('#saveEditAdcBtn').on('click', function () {
        const { porta, itemId } = prodAdcManager.currentEditing;
        if (!porta || !itemId) return;
        const cells = [
            $('#editCódAdcInput').val().trim(),
            $('#editDescAdcInput').val().trim(),
            $('#editUnidAdcInput').val().trim(),
            $('#editValorItemAdcInput').val().trim(),
            $('#editQtdAdcInput').val().trim()
        ];
        prodAdcManager.updateEditingItem(cells);
        bootstrap.Modal.getInstance(
            document.getElementById('editItemAdcModal')
        ).hide();
        prodAdcManager.clearEditing();
        syncAdicionalFromTable(porta);
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
        addItem(cells) {
            const idx = $('#itensTableForm tbody tr').length + 1;
            $('#itensTableForm tbody').append(`
                <tr>
                    <td data-label="#" class="mobile-2col">${idx}</td>
                    <td data-label="Forma Pgto.:" class="mobile-2col">${cells[0]}</td>
                    <td data-label="Valor:" class="mobile-2col" style="font-weight: bold; color: #2E8B57;">${cells[1]}</td>
                    <td data-label="Exc.:" class="mobile-2col">
                        <i class="fas fa-trash deleteFormaBtn" style="cursor: pointer;"></i>
                    </td>
                </tr>
            `);
        }
    };
    function addForma(formaId, formaPgto, valor) {
        const valorNumero = parseFloat(valor) || 0;
        const valorExibicao = valorNumero.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });

        formaManager.addItem([
            formaPgto,
            valorExibicao
        ]);

        const $ultimaLinha = $('#itensTableForm tbody tr:last');

        // ✅ GUARDA O ID DA FORMA NA LINHA
        $ultimaLinha
            .attr('data-forma-id', formaId)
            .data('forma-id', formaId)
            .data('valor', valorNumero);

        atualizarSubtotal();
        verificarTotalFormas();
        calcularValorForma();
        somaFormas();
    }

    function toNumberBR(v) {
        return parseFloat(
            String(v || '0')
                .replace(/\./g, '')
                .replace(',', '.')
        ) || 0;
    }
    function gerarJSONFormas() {
        const formas = [];
        console.log("=== INICIANDO gerarJSONFormas ===");
        $('#itensTableForm tbody tr').each(function (i) {
            const forma = $(this).find('td:eq(1)').text().trim();
            const valor = toNumberBR($(this).find('td:eq(2)').text());
            console.log(`Linha ${i + 1}`, { forma, valor });
            if (!forma || valor < 0.01) return;
            formas.push({ forma, valor });
        });
        console.log("JSON Formas Pgto FINAL:", formas);
        $('#id_json_formas_pgto').val(JSON.stringify(formas));
        return formas;
    }
    $('#confirmBtn').on('click', function () {
        gerarJSONFormas();
        const modalConfirm = bootstrap.Modal.getInstance(
            document.getElementById('staticBackdrop')
        );
        modalConfirm.hide();
        const loadingModal = new bootstrap.Modal(
            document.getElementById('loadingModal')
        );
        loadingModal.show();
        setTimeout(() => {
            $('#createForm')[0].submit();
        }, 200);
    });
    // Parser simplificado para valores monetários (aceita padrão americano ou brasileiro)
    function parseValor(str) {
        if (!str) return 0;
        str = str.trim();
        // Se tiver vírgula no final → formato BR
        if (str.match(/,\d{1,2}$/)) {
            return parseFloat(str.replace(/\./g, '').replace(',', '.')) || 0;
        }
        // Se tiver ponto no final → formato americano
        if (str.match(/\.\d{1,2}$/)) {
            return parseFloat(str.replace(/,/g, '')) || 0;
        }
        // Caso simples
        return parseFloat(str) || 0;
    }
    // Clique no botão de adicionar forma de pagamento
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
        const formaPgto = selectData[0]?.id;
        const valorStr  = $('#id_vl_form_pgto').val();
        const valor     = parseValor(valorStr);
        if (!formaPgto) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Forma de Pagamento deve ser informada!", cor_amarelo);
            $("#form_pgtoBtn").click();
            return;
        }
        if (valor <= 0) {
            toast("<i class='fa-solid fa-triangle-exclamation'></i> Informe um valor válido!", cor_amarelo);
            return;
        }
        if (formaJaExiste(formaPgto)) {
            toast(
                "<i class='fa-solid fa-triangle-exclamation'></i> Forma de pagamento já inclusa na tabela!",
                cor_amarelo
            );
            return;
        }

        $.ajax({
            url: "/formas_pgto/get/",
            method: "GET",
            data: { id: formaPgto },
            success: function (response) {
                addForma(response.id, response.descricao, valor);
                // limpa select e input
                $('#id_formas_pgto').val(null).trigger('change');
                $('#id_vl_form_pgto').val('');
                calcularValorForma();
                // ✅ AGORA SIM: a linha já existe
                gerarJSONFormas();
            },
            error: function () {
                toast("<i class='fa-solid fa-circle-xmark'></i> Erro ao buscar a Forma de Pagamento!", cor_vermelho);
            }
        });
    });
    $(document).on('click', '.deleteFormaBtn', function () {
        const row = $(this).closest('tr');
        row.remove();
        atualizarSubtotal();
        verificarTotalFormas();
        somaFormas();
        gerarJSONFormas();
    });
    // Clique no botão de adicionar produto principal
    $('#addItemProdBtn').on('click', function() {
        const codigo = $('#id_cod_prod').val().trim(); // Assumindo que você tem campos específicos para produtos adicionais
        const descricao = $('#id_desc_prod').val().trim();
        const unidade = $('#id_unidProd').val().trim();
        const valor = parseValor($('#id_vl_prod').val().trim());
        const quantidade = parseFloat($('#id_qtd_prod').val().trim());
        if (!codigo || !descricao || !unidade || isNaN(valor) || isNaN(quantidade) || quantidade <= 0) {
            return alert("Por favor, preencha todos os campos corretamente.");
        }
        // Adiciona o produto adicional à tabela
        prodAdcManager.addItem([codigo, descricao, unidade, valor.toFixed(2), valor.toFixed(2), quantidade.toFixed(2)]);
        // Limpa os campos de entrada
        $('#id_cod_prod').val('');
        $('#id_desc_prod').val('');
        $('#id_unidProd').val('');
        $('#id_vl_prod').val('');
        $('#id_qtd_prod').val('');
        $('#id_cod_prod').focus();
    });
    // Clique no botão de adicionar produto adicional
    $('#addItemProdAdcBtn').on('click', function() {
        const codigo = $('#id_cod_prod_adc').val().trim(); // Assumindo que você tem campos específicos para produtos adicionais
        const descricao = $('#id_desc_prod_adc').val().trim();
        const unidade = $('#id_unidProd_adc').val().trim();
        const valor = parseValor($('#id_vl_prod_adc').val().trim());
        const quantidade = parseFloat($('#id_qtd_prod_adc').val().trim());
        if (!codigo || !descricao || !unidade || isNaN(valor) || isNaN(quantidade) || quantidade <= 0) {
            return alert("Por favor, preencha todos os campos corretamente.");
        }
        // Adiciona o produto adicional à tabela
        prodAdcManager.addItem([codigo, descricao, unidade, 0.00, valor.toFixed(2), quantidade.toFixed(2), 0.00, (valor * quantidade).toFixed(2)]);
        // Limpa os campos de entrada
        $('#id_cod_prod_adc').val('');
        $('#id_desc_prod_adc').val('');
        $('#id_unidProd_adc').val('');
        $('#id_vl_prod_adc').val('');
        $('#id_qtd_prod_adc').val('');
        $('#id_cod_prod_adc').focus();
    });
    function Calc1() {
        const alt = parseFloat($('#id_alt').val().replace(',', '.'));
        let c1 = alt * 10;
        return c1.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function Calc2() {
        const re = parseFloat(Calc1());
        let c2 = re / 2;
        return c2.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
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
            if (productId.trim() === '') {
                return; // Sai da função se o campo estiver vazio
            }
            $.ajax({
                url: '/produtos/lista_ajax/', // Substitua pela URL correta da sua aplicação
                method: 'GET',
                data: {
                    s: productId,
                    tp: 'cod',
                    tp_prod: 'Principal' // Inclui o tipo de produto na requisição
                },
                success: function(response) {
                    if (response.produtos.length > 0) {
                        const produto = response.produtos[0];
                        $('#id_desc_prod').val(produto.desc_prod);
                        $('#id_unidProduto').val(produto.unidProd);
                        $('#id_vl_compra').val(produto.vl_compra);
                        $('#id_vl_prod').val(produto.vl_prod);
                        if (produto.vl_prod === "0.00" || produto.vl_prod === "") {
                            $('#id_vl_prod').focus();
                        } else {
                            $('#id_qtd_prod').focus();
                        }
                        const descricao = $('#id_desc_prod').val();
                        console.log('Cálculo do produto', descricao)
                        if (descricao === 'GUIAS' || descricao === 'TUBO DE AFASTAMENTO') {
                            console.log('Valor de id_qtd:', $('#id_qtd').val().replace(',', '.'));
                            console.log('Valor de id_alt_corte antes da leitura:', $('#id_alt_corte').val().replace(',', '.'));
                            let qtd = parseFloat($('#id_qtd').val().replace(',', '.'));
                            let at_c = parseFloat($('#id_alt_corte').val().replace(',', '.'));
                            if (!isNaN(qtd) && !isNaN(at_c)) {
                                let c = qtd * (at_c + 0.2) * 2;
                                console.log('Resultado do cálculo:', c.toFixed(2));
                                $('#id_qtd_prod').val(c.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                            } else {
                                $('#id_qtd_prod').val('0,00');
                            }
                        } else if (descricao === 'EIXO' || descricao === 'SOLEIRA') {
                            console.log('Valor de id_qtd antes da leitura:', $('#id_qtd').val().replace(',', '.'));
                            console.log('Valor de id_larg_corte antes da leitura:', $('#id_larg_corte').val().replace(',', '.'));
                            let qtd = parseFloat($('#id_qtd').val().replace(',', '.'));
                            let lg_c = parseFloat($('#id_larg_corte').val().replace(',', '.'));
                            if (!isNaN(qtd) && !isNaN(lg_c)) {
                                let c = qtd * lg_c;
                                console.log('Resultado do cálculo:', c.toFixed(2));
                                $('#id_qtd_prod').val(c.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                            } else {
                                $('#id_qtd_prod').val('0,00');
                            }
                        } else if (descricao === 'PERFIL DESLIZANTE') {
                            console.log('Valor de id_alt_corte antes da leitura:', $('#id_alt_corte').val().replace(',', '.'));
                            let at_c = parseFloat($('#id_alt_corte').val().replace(',', '.'));
                            if (!isNaN(at_c)) {
                                let c = at_c * 4;
                                console.log('Resultado do cálculo:', c.toFixed(2));
                                $('#id_qtd_prod').val(c.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                            } else {
                                $('#id_qtd_prod').val('0,00');
                            }
                        } else if (descricao === 'TRAVA LÂMINA') {
                            const resultado = Calc1(); // com C maiúsculo se a função for Calc1
                            if (!isNaN(parseFloat(resultado.replace(',', '.')))) {
                                $('#id_qtd_prod').val(resultado);
                            } else {
                                $('#id_qtd_prod').val('0,00');
                            }
                        } else if (descricao === 'LÂMINAS LISAS') {
                            console.log('Valor de id_m2 antes da leitura:', $('#id_m2').val().replace(',', '.'));
                            let m2 = parseFloat($('#id_m2').val().replace(',', '.'));
                            if (!isNaN(m2)) {
                                $('#id_qtd_prod').val(m2.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                            } else {
                                $('#id_qtd_prod').val('0,00');
                            }
                        }
                    } else {
                        toast("<i class='fa-solid fa-triangle-exclamation'></i> Código de produto não encontrado!", cor_amarelo);
                    }
                },
                error: function() {
                    toast("<i class='fa-solid fa-circle-xmark'></i> Erro ao buscar o produto. Tente novamente!", cor_vermelho);
                }
            });
        }
    });
    function calcularQtdProdutoPorContexto(produto) {
        const ctx = {
            larg: getFloat('#id_largura'),
            larg_c: getFloat('#id_larg_corte'),
            alt: getFloat('#id_altura'),
            alt_c: getFloat('#id_alt_corte'),
            m2: getFloat('#id_m2')
        };
        return calcularQtdPorRegra(produto, ctx);
    }

    function getFormProdutoByPorta(porta) {
        return $(`.form-produto[data-porta="${porta}"]`);
    }
    function getFormAdcByPorta(porta) {
        return $(`.form-adicional[data-porta="${porta}"]`);
    }
    function buscarProdutoPorCodigo($input, tipo) {

        const porta = Number($input.data('porta'));
        const cod = $input.val().trim();
        if (!cod) return;

        const isAdicional = tipo === 'Adicional';

        const $form = isAdicional
            ? getFormAdcByPorta(porta)
            : getFormProdutoByPorta(porta);

        console.log('🔍 Buscar', tipo, '| Porta:', porta, '| Código:', cod);

        $.ajax({
            url: '/produtos/lista_ajax/',
            method: 'GET',
            data: {
                s: cod,
                tp: 'cod',
                tp_prod: tipo
            },
            success(response) {

                if (!response.produtos?.length) {
                    toast("<i class='fa-solid fa-triangle-exclamation'></i> Código de produto não encontrado!", cor_amarelo);
                    return;
                }

                const produto = response.produtos[0];

                // 🔹 mapeamento correto dos campos
                const map = isAdicional ? {
                    desc: '.desc-prod-adc',
                    unid: '.unid-prod-adc',
                    valor: '.valor-prod-adc',
                    qtd: '.qtd-prod-adc'
                } : {
                    desc: '.desc-prod',
                    unid: '.unid-prod',
                    valor: '.valor-prod',
                    qtd: '.qtd-prod'
                };

                $form.find(map.desc).val(produto.desc_prod);
                $form.find(map.unid).val(produto.unidProd);
                $form.find(map.valor).val(produto.vl_prod);

                let qtdCalc = 0;
                try {
                    qtdCalc = calcularQtdProdutoPorContexto(produto, porta);
                } catch (e) {
                    console.warn('Erro regra:', e);
                }

                const $qtd = $form.find(map.qtd);

                if (qtdCalc > 0) {
                    $qtd.val(
                        qtdCalc.toLocaleString('en-US', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 2
                        })
                    ).data('auto', true);
                } else {
                    $qtd.val('').data('auto', false);
                }

                $form.find(map.valor).focus();
            },
            error() {
                toast("<i class='fa-solid fa-circle-xmark'></i> Erro ao buscar o produto. Tente novamente!", cor_vermelho);
            }
        });
    }
    $(document).on('blur', '.cod-prod', function () {
        buscarProdutoPorCodigo($(this), 'Principal');
    });

    $(document).on('keyup', '.cod-prod', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            buscarProdutoPorCodigo($(this), 'Principal');
        }
    });
    $(document).on('blur', '.cod-prod-adc', function () {
        buscarProdutoPorCodigo($(this), 'Adicional');
    });

    $(document).on('keyup', '.cod-prod-adc', function (e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            buscarProdutoPorCodigo($(this), 'Adicional');
        }
    });


    function carregarDadosCliente(clienteId) {
        if (clienteId) {
            $.ajax({
                url: '/clientes/lista_ajax/',
                method: 'GET',
                data: { term: clienteId },
                success: function(response) {
                    if (response.clientes.length > 0) {
                        const cliente = response.clientes[0];
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
                },
                error: function() {
                    console.error('Erro ao buscar os dados do cliente.');
                }
            });
        }
    }
    $('#id_cli').on('change', function() {
        carregarDadosCliente($(this).val());
    });
    carregarDadosCliente($('#id_cli').val());
    $('#button-addon2').on('click', function() {
        $('#produtoModal').modal('show');
    });
    $('#add-produtos').on('click', function() {
        $('#edProdModal').modal('show');
    });
    $('#edProdModal').on('shown.bs.modal', function () {
        $('#id_cod_produto').trigger('focus');
    });
    $('#add-prod').on('click', function() {
        $('#produtoModal').modal('show');
    });
    $('#button-addon3').on('click', function() {
        $('#produtoAdcModal').modal('show');
    });
    $('#pesquisar-produtos').on('click', function() {
        const termo = $('#campo-pesquisa-produto').val();
        $.ajax({
            url: '/produtos/lista_ajax/',
            method: 'GET',
            data: { s: termo, tp: 'desc', tp_prod: 'Principal' },
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
                                <td>${produto.id}</td>
                                <td>${produto.desc_prod}</td>
                                <td>${produto.unidProd}</td>
                                <td>${produto.estoque_prod}</td>
                                <td>${produto.vl_prod}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                } else {
                    tabela.append('<tr><td colspan="6">Nenhum produto encontrado.</td></tr>');
                }
            },
            error: function() {
            }
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
    // Entrada de Produtos
    $(document).on('click', '.prod-selec', function() {
        const id = $(this).data('id');
        const desc = $(this).data('desc');
        const gp = $(this).data('gp');
        const unid = $(this).data('unid');
        const vl = $(this).data('vl');
        $('#id_cod_produto').val(id);
        $('#id_desc_prod').val(desc);
        $('#id_grupoProd').val(gp);
        $('#id_unidProduto').val(unid);
        $('#id_vl_prod').val(vl);
        $('#id_cod_prod').focus();
        $('#produtoModal').modal('hide'); // Fecha o modal após a seleção
    });
    function carregarProdutos(page = 1) {
        const termo = $('#campo-pesquisa-produto').val();
        const tipo = $('#campo-tipo-produto').val();
        const grupo = $('#campo-grupo-produto').val();
        const unidade = $('#campo-unidade-produto').val();
        const pagina = $('#campo-pagina').val();
        $.ajax({
            url: '/produtos/lista_ajax_ent/',
            method: 'GET',
            data: {
                s: termo,
                tp: 'desc',
                tp_prod: tipo,
                gp_prod: grupo,
                unid_prod: unidade,
                num_pag: pagina,
                page: page
            },
            success: function(response) {
                const tabela = $('#produtos-lista');
                tabela.empty();
                if (response.produtos.length > 0) {
                    response.produtos.forEach(produto => {
                        const row = `
                            <tr>
                                <td style="width: 10px;">
                                    <button class="btn btn-sm btn-dark prod-selec"
                                            data-id="${produto.id}"
                                            data-desc="${produto.desc_prod}"
                                            data-gp="${produto.grupo}"
                                            data-unid="${produto.unidProd}"
                                            data-vl="${produto.vl_prod}"
                                            title="Selecionar"
                                            style="margin-left: 9px;">
                                        <i class="fa-regular fa-hand-pointer"></i>
                                    </button>
                                </td>
                                <td style="width: 10px;">${produto.id}</td>
                                <td>${produto.desc_prod}</td>
                                <td style="width: 20px;">${produto.tp_prod}</td>
                                <td style="width: 20px;">${produto.grupo}</td>
                                <td style="width: 20px;">${produto.unidProd}</td>
                                <td style="width: 20px;">${produto.estoque_prod}</td>
                                <td style="width: 20px;">${produto.vl_prod}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                } else {
                    tabela.append('<tr><td colspan="8" class="text-center">Nenhum produto encontrado.</td></tr>');
                }
                // montar paginação
                const paginacao = $('#paginacao');
                paginacao.empty();
                if (response.num_pages > 1) {
                    if (response.has_prev) {
                        paginacao.append(`<button class="btn btn-sm btn-outline-dark pag-btn" data-page="${response.page - 1}">Anterior</button>`);
                    }
                    for (let i = 1; i <= response.num_pages; i++) {
                        paginacao.append(`
                            <button class="btn btn-sm ${i === response.page ? 'btn-dark' : 'btn-outline-dark'} pag-btn" data-page="${i}">
                                ${i}
                            </button>
                        `);
                    }
                    if (response.has_next) {
                        paginacao.append(`<button class="btn btn-sm btn-outline-dark pag-btn" data-page="${response.page + 1}">Próximo</button>`);
                    }
                }
            }
        });
    }
    // clique no botão "Listar"
    $('#pesq-produtos').on('click', function() {
        carregarProdutos(1);
    });
    // clique nos botões de paginação
    $(document).on('click', '.pag-btn', function() {
        const page = $(this).data('page');
        carregarProdutos(page);
    });
    $(document).on('click', '.select-produto', function() {
        const id = $(this).data('id');
        const vl = $(this).data('vl');
        const formsetPrefix = "{{ formset.prefix }}";
        const totalForms = document.getElementById("id_" + formsetPrefix + "-TOTAL_FORMS");
        const formCount = parseInt(totalForms.value);
        // Clona a primeira linha do formset como base
        const newForm = document.querySelector("tbody tr").cloneNode(true);
        // Atualiza os atributos name/id para o novo índice
        newForm.querySelectorAll("input, select").forEach(function(input) {
            input.name = input.name.replace("-0-", "-" + formCount + "-");
            input.id = input.id.replace("-0-", "-" + formCount + "-");
            // Preenche com os dados do produto
            if (input.name.includes("produto")) {
                input.value = id; // ID do produto
            }
            if (input.name.includes("quantidade")) {
                input.value = ""; // começa vazio para o usuário editar
            }
            if (input.name.includes("preco_unitario")) {
                input.value = vl; // valor sugerido
            }
        });
        // Adiciona a nova linha na tabela
        document.querySelector("#tabela-produtos tbody").appendChild(newForm);
        // Atualiza o contador do formset
        totalForms.value = formCount + 1;
        // Fecha o modal
        $('#produtoModal').modal('hide');
    });
    $('#pesquisar-produtos-adicionais').on('click', function() {
        const termo = $('#campo-pesquisa-produto-adicional').val();
        $.ajax({
            url: '/produtos/lista_ajax/',
            method: 'GET',
            data: { s: termo, tp: 'desc', tp_prod: 'Adicional' },
            success: function(response) {
                const tabela = $('#produtosAdc-lista');
                tabela.empty();
                if (response.produtos.length > 0) {
                    response.produtos.forEach(produto => {
                        const row = `
                            <tr>
                                <td style="width: 20px;">
                                    <button class="btn btn-sm btn-dark selecionar-produto-adicional" data-id="${produto.id}" data-desc="${produto.desc_prod}" data-unid="${produto.unidProd}" data-vl="${produto.vl_prod}" title="Selecionar" style="margin-left: 9px;">
                                        <i class="fa-regular fa-hand-pointer"></i>
                                    </button>
                                </td>
                                <td>${produto.id}</td>
                                <td>${produto.desc_prod}</td>
                                <td>${produto.unidProd}</td>
                                <td>${produto.estoque_prod}</td>
                                <td>${produto.vl_prod}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                } else {
                    tabela.append('<tr><td colspan="6">Nenhum produto encontrado.</td></tr>');
                }
            },
            error: function() {
            }
        });
    });
    $(document).on('click', '.selecionar-produto-adicional', function() {
        const id = $(this).data('id');
        const desc = $(this).data('desc');
        const unidade = $(this).data('unid');
        const vl = $(this).data('vl');
        $('#id_cod_prod_adc').val(id);
        $('#id_desc_prod_adc').val(desc);
        $('#id_unidProd_adc').val(unidade);
        $('#id_vl_prod_adc').val(vl);
        $('#id_cod_prod_adc').focus();
        $('#produtoAdcModal').modal('hide'); // Fecha o modal após a seleção
    });
    var cores = {
        "Preto": "#000000", "Branco": "#FFFFFF", "Amarelo": "#FFFF00",
        "Vermelho": "#FF0000", "Roxo Açaí": "#6A0DAD", "Azul Pepsi": "#0033A0",
        "Azul Claro": "#ADD8E6", "Cinza Claro": "#D3D3D3", "Cinza Grafite": "#4F4F4F",
        "Verde": "#008000", "Bege": "#F5F5DC", "Bege Areia": "#D7C9A3", "Marrom": "#8B4513",
        "Marrom Café": "#4B2E2B", "Laranja": "#FFA500", "Azul Royal": "#4169E1",
        "Azul Marinho": "#000080", "Verde Musgo": "#556B2F", "Verde Bandeira": "#009739",
        "Vinho": "#8B0000", "Prata": "#C0C0C0"
    };
    function pintarOptions() {
        $("#id_cor option").each(function () {
            let texto = $(this).text();
            let cor = cores[texto];
            if (cor) {
                $(this).css({
                    "background-color": cor,
                    "color": isCorEscura(cor) ? "#FFFFFF" : "#000000"
                });
            }
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
        $("#id_cor").css({
            "background-color": novaCor,
            "color": isCorEscura(novaCor) ? "#FFFFFF" : "#000000"
        });
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
        if (tipoChave === 'CPF') {
            inputChavePix.mask("000.000.000-00");
        } else if (tipoChave === 'CNPJ') {
            inputChavePix.mask("00.000.000/0000-00");
        } else if (tipoChave === 'Telefone') {
            inputChavePix.mask('(00) 00000-0000');
        } else if (tipoChave === 'E-mail') {
            inputChavePix.attr("type", "email"); // para validação nativa de email
        } else if (tipoChave === 'Chave Aleatória') {
            // Máscara para UUID v4
            inputChavePix.mask('AAAAAAAA-AAAA-AAAA-AAAA-AAAAAAAAAAAA', {
                translation: {
                    'A': { pattern: /[a-fA-F0-9]/ }
                },
                placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
            });
        }
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
            $('#loadingModal').modal('hide');
        } else {
            labelCpfCnpj.text("CNPJ*");
            labelnome.text("Razão Social*");
            labelapelido.text("Fantasia*");
            labelIE.text("Inscrição Estadual");
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
        if (r.length > 11) {
            r = r.replace(/^(\d{2})(\d{5})(\d{4}).*/, "($1) $2-$3");
        } else if (r.length === 11) {
            r = r.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
        } else if (r.length === 10) {
            r = r.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");
        } else if (r.length > 2) {
            r = r.replace(/^(\d{2})(\d{0,5})/, "($1) $2");
        } else if (r.length > 0) {
            r = r.replace(/^(\d*)/, "($1");
        }
        return r;
    }
    $("#id_tel").on("input", function () {
        maskInput($(this));
    });
    function mascaraFone(phone) {
        let cleanedPhone = phone.replace(/\D/g, '');
        if (cleanedPhone.length > 2) {
            if (cleanedPhone[2] === '8' || cleanedPhone[2] === '9') {
                cleanedPhone = cleanedPhone.slice(0, 2) + '9' + cleanedPhone.slice(2);
                return cleanedPhone.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
            }
            else if (cleanedPhone[2] === '4' || cleanedPhone[2] === '5' || cleanedPhone[2] === '6') {
                return cleanedPhone.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
            }
        }
        return cleanedPhone.replace(/^(\d{2})(\d{4,5})(\d{4})$/, '($1) $2-$3');
    }
    $("#id_cpf_cnpj").on("blur", function () {
        let tipoPessoa = $("#id_pessoa").val();
        let cnpj = $(this).val().replace(/\D/g, ""); // Remove caracteres não numéricos
        if (tipoPessoa === "Jurídica" && cnpj.length === 14) {
            $('#loadingModal').modal('show');
            fetch(`https://open.cnpja.com/office/${cnpj}`)
                .then(response => response.json())
                .then(data => {
                    console.log(data);
                    if (data.company) {
                        $('#id_razao_social').val((data.company.name || "").toUpperCase());
                        $('#id_fantasia').val((data.alias || "").toUpperCase());
                    }
                    if (data.registrations && data.registrations.length > 0) {
                        let ieNumber = data.registrations[0].number || "";
                        if (data.registrations[0].state === "PA") {
                            ieNumber = ieNumber.replace(/^(\d{2})(\d{3})(\d{3})(\d{1})$/, '$1.$2.$3-$4');
                        }
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
                    verificarOuCriarLocalizacao(estado, cidade, bairro)
                        .then(response => {
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
                    if (data.emails && data.emails.length > 0) {
                        $('#id_email').val(data.emails[0].address || "");
                    }
                })
                .catch(error => console.error('Erro ao buscar CNPJ:', error))
                .finally(() => {
                    setTimeout(() => {
                        $('#loadingModal').modal('hide');
                    }, 500); // ajuste aqui o tempo desejado
                });
        }
    });
    function atualizarSelect(selector, nome, id) {
        const option = new Option(nome, id, true, true);
        $(selector).append(option).trigger('change');
    }
    function verificarOuCriarLocalizacao(estado, cidade, bairro) {
        const url = `/verificar-localizacao/?estado=${estado}&cidade=${cidade}&bairro=${bairro}`;
        return fetch(url)
            .then(response => response.json())
            .catch(error => console.error('Erro na verificação de localização:', error));
    }
    $("#id_empresa").on("blur", function() {
        let empresaId = $(this).val().trim();
        if (empresaId) {
            $('#loadingModal').modal('show');
            $.ajax({
                url: "/usuarios/buscar_empresa/",
                method: "GET",
                data: { id_empresa: empresaId },
                success: function(response) {
                    if (response.success) {
                        let fantasia = response.fantasia ? response.fantasia.toUpperCase() : "";
                        if (fantasia) {
                            $("#fantasia_fantasia").val(fantasia);
                            $("#container_fantasia").removeAttr("hidden"); // Exibe o campo
                            setTimeout(() => {
                                $('#id_username').focus(); // Aplica o foco depois de 3 segundos
                            }, 1500);
                            toastErrorShown = false; // Reseta o estado para futuras verificações
                        }
                    } else {
                        $("#container_fantasia").attr("hidden", true);
                        $('#id_empresa').focus();
                        let errorMessage = response.warning || response.error || "ID inexistente na base de dados";
                        let backgroundColor = response.warning ? "linear-gradient(to right, #d58300, #ffc93b)" : "linear-gradient(to right, #ff416c, #ff4b2b)";
                        if (!toastErrorShown) { // Só exibe a mensagem se ainda não foi mostrada
                            toastErrorShown = true;
                            Toastify({
                                text: errorMessage,
                                duration: 5000,
                                gravity: "top",
                                position: "center",
                                backgroundColor: backgroundColor,
                                stopOnFocus: true,
                                escapeMarkup: false,
                            }).showToast();
                        }
                    }
                },
                error: function() {
                    $("#container_fantasia").attr("hidden", true);
                    $('#id_empresa').focus();
                },
                complete: function() {
                    setTimeout(() => {
                        $('#loadingModal').modal('hide');
                    }, 1000);
                }
            });
        } else {
            $("#container_fantasia").attr("hidden", true);
        }
    });
    $("#id_empresa").on("input", function() {
        toastErrorShown = false;
    });
    let errorDiv = $(".alert.alert-block.alert-danger");
    if (errorDiv.length) {
        let errorMessage = errorDiv.find("li").text();
        errorDiv.hide();
        Toastify({
            text: errorMessage,
            duration: 5000,
            gravity: "top",
            position: "center",
            backgroundColor: "linear-gradient(to right, #ff416c, #ff4b2b)",
            stopOnFocus: true,
            escapeMarkup: false,
        }).showToast();
    }
    let messageContainer1 = $("#toast-messages");
    if (messageContainer1.length) {
        let messages = [];
        try {
            messages = JSON.parse(messageContainer1.attr("data-messages"));
        } catch (e) {
            console.error("Erro ao analisar JSON:", e);
            messages = [];  // ← Corrige o erro
        }
        if (messages && messages.length > 0) {
            messages.forEach(msg => {
                if (msg && msg.text) {
                    Toastify({
                        text: `<span>${msg.text}</span>`,
                        duration: 5000,
                        gravity: "top",
                        position: "center",
                        backgroundColor: "linear-gradient(to right, #ff416c, #ff4b2b)",
                        stopOnFocus: true,
                        escapeMarkup: false,
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
            Toastify({
                text: `<span style="display: flex; align-items: center; gap: 8px;">
                            <strong>${icon}</strong> ${msg.text}
                       </span>`,
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: bgColor,
                stopOnFocus: true,
                escapeMarkup: false, // Permite renderizar HTML
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
                toast("<i class='fa-solid fa-circle-check'></i> Link copiado!", cor_verde);
            }).catch(err => console.error("Erro ao copiar: ", err));
        } else {
            // Fallback para navegadores antigos
            let tempInput = $("<input>");
            $("body").append(tempInput);
            tempInput.val(link).select();
            document.execCommand("copy");
            tempInput.remove();
            toast("<i class='fa-solid fa-circle-check'></i> Link copiado!", cor_verde);
        }
    });
    document.addEventListener("DOMContentLoaded", function() {
        var link = document.createElement("link");
        link.rel = "shortcut icon";
        link.href = "https://allitec.pythonanywhere.com/static/img/favicon.ico";
        link.type = "image/x-icon";
        document.head.appendChild(link);
    });
    $('#doc-botao').on('mouseenter', function () {
        $('#icone-botao').css('color', 'white'); // Altere para a cor desejada
    });
    $('#doc-botao').on('mouseleave', function () {
        $('#icone-botao').css('color', 'black'); // Retorne à cor original
    });
    const $checkbox = $("#toggle-data-agendamento");
    const $dataAgendamento = $("#id_data_agendamento");
    $checkbox.change(function () {
        if ($(this).is(":checked")) {
            $dataAgendamento.prop("disabled", false);
        } else {
            $dataAgendamento.prop("disabled", true).val("");
        }
    });
    function updateMassChangesButton() {
        const taskCheckboxes = $(".task-checkbox");
        const massChangesButton = $("#update-selected");
        if (!massChangesButton.length) {
            console.warn("O botão 'update-selected' não foi encontrado.");
            return;
        }
        const anyChecked = taskCheckboxes.is(":checked");
        massChangesButton.prop("disabled", !anyChecked);
    }
    // Marca ou desmarca todos
    function toggleSelectAll(forceCheck = null) {
        const selectAllCheckbox = $("#select-all");
        const taskCheckboxes = $(".task-checkbox");
        // Se forceCheck for nulo, usa o estado atual do checkbox
        const isChecked = forceCheck !== null ? forceCheck : selectAllCheckbox.is(":checked");
        // Remove estado indeterminado
        selectAllCheckbox.prop("indeterminate", false);
        selectAllCheckbox.prop("checked", isChecked);
        // Aplica a todos
        taskCheckboxes.prop("checked", isChecked);
        updateMassChangesButton();
    }
    // Clicar em qualquer parte do <th> alterna o checkbox principal
    $("th:has(#select-all)").on("click", function (e) {
        const checkbox = $("#select-all");
        // Evita conflito se o clique for exatamente no checkbox
        if ($(e.target).is("#select-all")) return;
        // Alterna o estado do checkbox
        const shouldCheck = !checkbox.prop("checked");
        toggleSelectAll(shouldCheck);
    });
    // Clique direto no checkbox do thead (mesma lógica)
    $("#select-all").on("click", function (e) {
        e.stopPropagation(); // Evita duplicar clique
        toggleSelectAll($(this).is(":checked"));
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
        } else {
            selectAllCheckbox.prop("indeterminate", true);
        }
    }
    // Corrige comportamento de labels de switches
    $(".form-check-label").click(function (e) {
        e.preventDefault();
        const switchInput = $("#" + $(this).attr("for"));
        switchInput.prop("checked", !switchInput.is(":checked"));
    });
    // Expõe funções globalmente (caso use inline)
    window.toggleSelectAll = toggleSelectAll;
    window.toggleTaskCheckbox = toggleTaskCheckbox;
    window.checkIfAllSelected = checkIfAllSelected;
    window.updateMassChangesButton = updateMassChangesButton;
    function closeGerarVisitasModal() {
        var modalInstance = bootstrap.Modal.getInstance($("#gerarVisitasModal")[0]);
        if (modalInstance) modalInstance.hide();
        $("body").removeClass("modal-open");
        $(".modal-backdrop").remove();
        $("body").css({
            overflow: "",
            paddingRight: "",
        });
    }
    function closeStaticBackdrop() {
        var modalInstance = bootstrap.Modal.getInstance($("#staticBackdrop")[0]);
        if (modalInstance) modalInstance.hide();
        $("body").removeClass("modal-open");
        $(".modal-backdrop").remove();
        $("body").css({
            overflow: "",
            paddingRight: "",
        });
    }
    $(document).on("click", ".btn-confirmar", function () {
        const url = $(this).data("url");
        const id  = $(this).data("orcamento-id");
        const confirmModalEl = document.getElementById("modal-" + id);
        const confirmModal   = bootstrap.Modal.getInstance(confirmModalEl);
        const menuModalEl = document.getElementById("menuModal" + id);
        const menuModal   = bootstrap.Modal.getInstance(menuModalEl);
        if (confirmModal) {
            confirmModal.hide();
        }
        setTimeout(function () {
            if (menuModal) {
                menuModal.hide();
            }
        }, 200);
        setTimeout(function () {
            window.location.href = url;
        }, 400);
    });
    // Botão "Não" no modal 'staticBackdrop'
    $("#btnRecusa").on("click", function () {
        closeStaticBackdrop();
    });
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
        // Fecha ambos os modais após a exclusão
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
        if (event.key.toLowerCase() === "s") {
            modalConfirm.find(".confirm-delete").trigger("click");
        } else if (event.key.toLowerCase() === "n") {
            modalConfirm.find(".btn-cancel").trigger("click");
        }
    });
    $(document).on("click", "#botoes-modal", function () {
        var actionType = $(this).data("id"); // Identifica a ação associada ao botão
        var menuModal = bootstrap.Modal.getInstance($("#menuModal" + actionType)[0]);
        var docModal = bootstrap.Modal.getInstance($("#documentModal" + actionType)[0]);// Obtem o modal atualmente aberto
        if (menuModal) {
            menuModal.hide();
        }
        if (docModal) {
            docModal.hide();
        }
    });
    $("#staticBackdrop").on("keydown", function (e) {
        var keyCode = e.which || e.keyCode;
        if (keyCode === 83) { // 'S'
            $("#confirmBtn").click();
        } else if (keyCode === 78 || keyCode === 27) { // 'N' ou 'ESC'
            closeStaticBackdrop();
        }
    });
    $("[id^='modal-']").on("keydown", function (e) {
        const key = e.which || e.keyCode;
        if (key === 83) { // S
            $("#confirmBtn").click();
        }
        else if (key === 78 || key === 27) { // N ou ESC
            closeStaticBackdrop();
        }
    });
    $("#btnCloseGerarVisitas").on("click", function () {
        closeGerarVisitasModal();
    });
    $("#gerarVisitasModal").on("keydown", function (e) {
        var keyCode = e.which || e.keyCode;
        if (keyCode === 27) { // 'ESC'
            closeGerarVisitasModal();
        }
    });
    $('#gerarVisitasModal').on('shown.bs.modal', function () {
        $('#cidade_origem').focus();
    });
    // Função de Desconto - Orçamentos
    function extrairNumero(str) {
        return parseFloat(
            str
                .replace('R$ ', '')
                .replace(/\./g, '') // remove separador de milhar
                .replace(',', '.')  // vírgula vira decimal
                .trim()
        ) || 0;
    }
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
            $('#auxiliar_desconto').val(
                isNaN(percentual) ? '0.00' : percentual.toFixed(2)
            );
            return campo_desconto;
        } else {
            labelNomeCampo.text("Percentual:");
            simboloInputCampo.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliar.text("R$");
            let valorCalculado = (subtotal_orcamento * campo_desconto) / 100;
            $('#auxiliar_desconto').val(
                isNaN(valorCalculado) ? '0.00' : valorCalculado.toFixed(2)
            );
        }
    }
    $("#campo_desconto, #tipo_desconto").on("input keyup change", function () {
        calcularDescontoAtualizarAuxiliar();
    });
    // Evento ao abrir o modal
    $('#modalDesconto').on('shown.bs.modal', function () {
        $('#tipo_desconto').focus();
    });
    // Evento botão confirmar
    $('#confirmarDesconto').on('click', function () {
        let desconto = calcularDescontoAtualizarAuxiliar();
        desconto = parseFloat(desconto) || 0;
        $('#id_desconto').val(desconto.toFixed(2));
        $('#desconto_txt').text('R$ ' + desconto.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }));
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
            $('#auxiliar_acrescimo').val(
                isNaN(percentual) ? '0.00' : percentual.toFixed(2)
            );
            return campo_acrescimo;
        } else {
            labelNomeCampo.text("Percentual:");
            simboloInputCampoAc.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliarAc.text("R$");
            let valorCalculado = ((subtotal_orcamento * campo_acrescimo) / 100);
            $('#auxiliar_acrescimo').val(
                isNaN(valorCalculado) ? '0.00' : valorCalculado.toFixed(2)
            );
        }
    }
    $("#campo_acrescimo, #tipo_acrescimo").on("input keyup change", function () {
        calcularAcrescimoAtualizarAuxiliar();
    });
    // Evento ao abrir o modal
    $('#modalAcrescimo').on('shown.bs.modal', function () {
        $('#tipo_acrescimo').focus();
    });
    // Evento botão confirmar
    $('#confirmarAcrescimo').on('click', function () {
        let acrescimo = calcularAcrescimoAtualizarAuxiliar();
        $('#id_acrescimo').val(acrescimo.toFixed(2));
        $('#acrescimo_txt').text('R$ ' + acrescimo.toLocaleString('pt-BR', {
            minimumFractionDigits: 2, maximumFractionDigits: 2
        }));
        $('#modalAcrescimo').modal('hide');
        atualizarSubtotal();
    });
    $('#exampleModal').on('shown.bs.modal', function () {
       $('#cid_emp').focus();
    });
    $('#openModalBtn1').click(function () {
        $('#staticBackdrop2').modal('show');
        $('#staticBackdrop2').on('shown.bs.modal', function () {
            $(this).focus();
        });
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
        if (keyCode === 83) { // 'S' - Confirmar
            $("#confirmBtn1").click();
        } else if (keyCode === 78 || keyCode === 27) { // 'N' ou 'ESC' - Fechar apenas o modal de confirmação
            $("#btnRecusa1").click();
        }
    });
    $('#logo-preview').on('click', function() {
        $('#id_logo').click();// Simula o clique no input de arquivo
    });
    $('#id_logo').on('change', function(event) {
        var reader = new FileReader();
        reader.onload = function(e) {
            $('#logo-preview').attr('src', e.target.result);  // Troca a imagem
        };
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
    $('#switchData').change(function () {
        verificarEstadoSwitch('#switchData', '#dtVisita, #pxVisita');
    });
    $('#switchIdSis').change(function () {
        verificarEstadoSwitch('#switchIdSis', '#prin');
    });
    $('#switchIdSis1').change(function () {
        verificarEstadoSwitch('#switchIdSis1', '#prin1');
    });
    function verificarEstadoSwitch(selector, target) {
        $(target).prop('disabled', !$(selector).prop('checked'));
    }
    // Inicializa o estado ao carregar a página
    verificarEstadoSwitch('#switchEmp', '#unidade1');
    verificarEstadoSwitch('#switchSit', '#grupo1');
    verificarEstadoSwitch('#switchMarca', '#marca1');
    // Quando o switch muda, habilita ou desabilita o campo
    $('#switchEmp').change(function () {
        verificarEstadoSwitch('#switchEmp', '#unidade1');
    });
    $('#switchSit').change(function () {
        verificarEstadoSwitch('#switchSit', '#grupo1');
    });
    $('#switchMarca').change(function () {
        verificarEstadoSwitch('#switchMarca', '#marca1');
    });
    // Ao clicar no label, marca/desmarca o switch e dispara o change para atualizar o campo
    $('label[for="switchEmp"], label[for="switchSit"], label[for="switchMarca"]').on('click', function () {
        const switchId = $(this).attr('for');
        setTimeout(() => {
            let target;
            if (switchId === 'switchEmp') target = '#unidade1';
            else if (switchId === 'switchSit') target = '#grupo1';
            else if (switchId === 'switchMarca') target = '#marca1';

            verificarEstadoSwitch('#' + switchId, target);
        }, 10);
    });
    $(document).on('click', '#pesquisar-produtos, #pesquisar-produtos-adicionais, #button-addon3, #button-addon2, .selecionar-produto-adicional, .selecionar-produto', function(e) {
        e.preventDefault();
        $("#id_preco_unit").focus();
    });
    $('#voltarBtn').click(function(e) {
        e.preventDefault();
        $('#loadingModal').modal('hide'); // Esconde o modal
        $(this).prop('disabled', true);
        var previousPage = document.referrer;
        if (previousPage) {
            setTimeout(function() {
                window.location.href = previousPage;
            }, 300);
        } else {
            setTimeout(function() {
                window.location.href = '/lista/';
            }, 300);
        }
    });
    $(window).on('beforeunload', function() {
        $('#loadingModal').modal('show');
    });
    $(window).on('load', function() {
        $('#loadingModal').modal('hide');
    });
    $('#id_solicitante, #tecnico').select2({
        allowClear: true,
        placeholder: 'Selecione um técnico',
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            // cria o layout: ID em cima e Nome abaixo
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            // mostra apenas o nome após selecionar
            return data.text;
        },
        ajax: {
            url: "/tecnicos/lista_ajax/",  // URL correta
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term  // termo de busca
                };
            },
            processResults: function(data) {
                return {
                    results: data.tecnicos.map(function(tecnico) {
                        return {
                            id: tecnico.id,
                            text: tecnico.nome
                        };
                    })
                };
            },
            cache: true
        },
        language: {
            inputTooShort: function() {
                return 'Por favor, insira 1 ou mais caracteres';
            },
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#id_filial').select2({
        allowClear: true,
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            // cria o layout: ID em cima e Nome abaixo
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        placeholder: 'Selecione uma filial',
        ajax: {
            url: "/ajax/filiais-vinculadas/",  // URL correta
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term  // termo de busca
                };
            },
            processResults: function (data) {
                return {
                    results: data.results
                };
            },
            cache: true
        },
        language: {
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#vinc_emp, #id_vinc_emp').select2({
        allowClear: true,
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        placeholder: 'Selecione uma filial',
        ajax: {
            url: "/ajax/filiais-vinculadas/",  // URL correta
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term ? params.term.toUpperCase() : ""
                };
            },
            processResults: function (data) {
                return {
                    results: data.results
                };
            },
            cache: true
        },
        language: {
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#emp').select2({
        allowClear: true,
        placeholder: 'Selecione uma empresa',
        ajax: {
            url: "/empresas/lista_ajax/",  // URL correta
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term  // termo de busca
                };
            },
            processResults: function (data) {
                return {
                    results: data.results
                };
            },
            cache: true
        },
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        language: {
            inputTooShort: function() {
                return 'Por favor, insira 1 ou mais caracteres';
            },
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#id_form_pgto').select2({
        placeholder: 'Escolha uma forma',
        allowClear: true
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#userSelect').select2({
        placeholder: 'Escolha um usuário',
        allowClear: true
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#id_tp_chave').select2({
        placeholder: 'Escolha uma opção',
        allowClear: true
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#select-all').on('click', function() {
        var checkboxes = $('input[name="multi"]');
        checkboxes.prop('checked', this.checked);
        toggleUpdateButton();
    });
    $('.task-checkbox').on('change', toggleUpdateButton);
    function toggleUpdateButton() {
        var selectedCheckboxes = $('.task-checkbox:checked');
        $('#update-selected').prop('disabled', selectedCheckboxes.length === 0);
    }
    $('#update-selected').on('click', function() {
        var selectedCheckboxes = $('.task-checkbox:checked');
        var multiIds = selectedCheckboxes.map(function() {
            return this.value;
        }).get();
        var container = $('#multi-hidden-container');
        container.empty();
        $.each(multiIds, function(index, id) {
            var input = $('<input>').attr({
                type: 'hidden',
                name: 'multi',  // Certifique-se de que o nome está correto e igual ao que é esperado na view
                value: id
            });
            container.append(input);
        });
        $('#selected-count').text(multiIds.length);
    });
    $('#mdAttTbPreco').on('click', function() {
        var selectedCheckboxes = $('.task-checkbox:checked');
        var multiIds = selectedCheckboxes.map(function() {
            return this.value;
        }).get();
        var container = $('#multi-hidden-cont');
        container.empty();
        $.each(multiIds, function(index, id) {
            var input = $('<input>').attr({
                type: 'hidden',
                name: 'prod-prec',  // Certifique-se de que o nome está correto e igual ao que é esperado na view
                value: id
            });
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
            else if (cleanedPhone[2] === '4' || cleanedPhone[2] === '5' || cleanedPhone[2] === '6') {
                return cleanedPhone.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
            }
        }
        return cleanedPhone.replace(/^(\d{2})(\d{4,5})(\d{4})$/, '($1) $2-$3');
    }
    function removeAccents(str) {
        const accents = [
            {base: 'a', letters: /[áàãâä]/g},
            {base: 'e', letters: /[éèêë]/g},
            {base: 'i', letters: /[íìîï]/g},
            {base: 'o', letters: /[óòõôö]/g},
            {base: 'u', letters: /[úùûü]/g},
            {base: 'c', letters: /[ç]/g},
            {base: 'n', letters: /[ñ]/g},
        ];
        accents.forEach(function(accent) {
            str = str.replace(accent.letters, accent.base);
        });
        return str;
    }
    // API De Consulta CNPJ Com Inscrição Estadual
    function abreviarEndereco(endereco) {
        const substituicoes = {
            'AVENIDA': 'AV.',
            'TRAVESSA': 'TV.',
            'RUA': 'R.',
            'RODOVIA': 'ROD.',
            'ESTRADA': 'EST.',
            'ALAMEDA': 'AL.',
            'LARGO': 'LG.',
            'PRACA': 'PC.',
            'PRAÇA': 'PC.',
            'VILA': 'VL.'
        };
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
        $('#loadingModal').modal('show');
        fetch(`https://open.cnpja.com/office/${cnpj}`)
        .then(response => response.json())
        .then(data => {
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
            // Verifica e atualiza os campos Select2
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
            if (data.phones && data.phones.length > 0) {
                $('#id_tel, #id_contato_administrador').val(mascaraFone(data.phones[0].area + " " + data.phones[0].number || ""));
            }
            if (data.emails && data.emails.length > 0) {
                $('#id_email, #id_email_administrador').val(data.emails[0].address || "");
            }
            $('#id_cnae_cod').val(data.mainActivity.id || "");
            $('#id_cnae_desc').val((data.mainActivity.text || "").toUpperCase());
            if (data.company.members?.length > 0) {
                $('#id_administrador').val((data.company.members[0].person.name || "").toUpperCase());
            }
        })
        .catch(error => console.error('Erro ao buscar CNPJ:', error))
        .finally(() => {
            setTimeout(() => {
                $('#loadingModal').modal('hide');
            }, 2000);
        });
    });
    $('#id_bairro_fil, #id_bairro').select2({
        allowClear: true,
        placeholder: 'Selecione um bairro',
        ajax: {
            url: "/bairros/lista_ajax/",  // URL correta
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term  // termo de busca
                };
            },
            processResults: function(data) {
                return {
                    results: data.bairros.map(function(bairro) {
                        return {
                            id: bairro.id,
                            text: bairro.nome_bairro
                        };
                    })
                };
            },
            cache: true
        },
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        language: {
            inputTooShort: function() {
                return 'Por favor, insira 1 ou mais caracteres';
            },
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#id_cidade_fil, #id_cidade').select2({
        allowClear: true,
        placeholder: 'Selecione uma cidade',
        ajax: {
            url: "/cidades/lista_ajax/",  // URL correta
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term  // termo de busca
                };
            },
            processResults: function(data) {
                return {
                    results: data.cidades.map(function(cidade) {
                        return {
                            id: cidade.id,
                            text: cidade.nome_cidade
                        };
                    })
                };
            },
            cache: true
        },
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        language: {
            inputTooShort: function() {
                return 'Por favor, insira 1 ou mais caracteres';
            },
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#id_uf').select2({
        allowClear: true,
        placeholder: 'Selecione um estado',
        ajax: {
            url: "/estados/lista_ajax/",  // URL correta
            dataType: 'json',
            delay: 250,
            data: function (params) {
                return {
                    term: params.term  // termo de busca
                };
            },
            processResults: function(data) {
                return {
                    results: data.estados.map(function(estado) {
                        return {
                            id: estado.id,
                            text: estado.nome_estado
                        };
                    })
                };
            },
            cache: true
        },
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        language: {
            inputTooShort: function() {
                return 'Por favor, insira 1 ou mais caracteres';
            },
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    function listen() {
        const options = {
            method: "GET",
            mode: "cors",
            cache: "default" // corrigido de "caches"
        };
        $('#id_cep').on('blur', function() {
            let cep = $(this).val().replace("-", "").trim();
            if (cep.length < 8) {
                console.warn("CEP inválido.");
                return;
            }
            $('#loadingModal').modal('show');
            fetch(`https://viacep.com.br/ws/${cep}/json/`, options)
                .then(response => response.json())
                .then(data => {
                    if (data.erro) {
                        console.error("CEP não encontrado.");
                        setTimeout(() => $('#loadingModal').modal('hide'), 500);
                        return;
                    }
                    console.log(data);
                    const estado = (data.uf || "").toUpperCase();
                    const cidade = (data.localidade ? removeAccents(data.localidade) : "").toUpperCase();
                    const bairro = (data.bairro || "").toUpperCase();
                    verificarOuCriarLocalizacao(estado, cidade, bairro)
                        .then(response => {
                            if (!response.error) {
                                atualizarSelect('#id_uf', response.estado_nome, response.estado_id);
                                atualizarSelect('#id_cidade, #id_cidade_fil', response.cidade_nome, response.cidade_id);
                                atualizarSelect('#id_bairro, #id_bairro_fil', response.bairro_nome, response.bairro_id);
                            }
                            setTimeout(() => $('#loadingModal').modal('hide'), 500); // ✅ delay de 500ms
                        })
                        .catch(error => {
                            console.error('Erro na verificação de localização:', error);
                            setTimeout(() => $('#loadingModal').modal('hide'), 500);
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
                    setTimeout(() => $('#loadingModal').modal('hide'), 500);
                });
        });
    }
    function atualizarSelect(selector, nome, id) {
        const option = new Option(nome, id, true, true);
        $(selector).append(option).trigger('change');
    }
    function verificarOuCriarLocalizacao(estado, cidade, bairro) {
        const url = `/verificar-localizacao/?estado=${estado}&cidade=${cidade}&bairro=${bairro}`;
        return fetch(url)
            .then(response => response.json())
            .catch(error => console.error('Erro na verificação de localização:', error));
    }
    function init() {
        listen();
    }
    $(document).ready(init);
    
    var endSecao = $('#enderecos');
    function hideAllSections1() {
        $('.form-section').hide();
    }
    function updateButtonStyle1(activeBt, bt1, bt2) {
        activeBt?.addClass('btn-ativo').removeClass('btn-inativo');
        bt1?.removeClass('btn-ativo btn-inativo');
        bt2?.removeClass('btn-ativo btn-inativo');
    }

    function showSection1(sectionId, activeBt, bt1, bt2) {
        hideAllSections1();
        $('#' + sectionId).show();
        updateButtonStyle1(activeBt, bt1, bt2);
    }
    hideAllSections1();
    $(endSecao).show();
    const endBt = $('#endBtn');
    const compBt = $('#complBtn');
    const dadosRespBt = $('#dadosRespBtn');
    $(endBt).on('click', function() {
        showSection1('enderecos', endBt, compBt, dadosRespBt);
    });
    $(compBt).on('click', function() {
        showSection1('complementos', compBt, endBt, dadosRespBt);
    });
    $(dadosRespBt).on('click', function() {
        showSection1('dadosResponsavel', dadosRespBt, endBt, compBt);
    });
    // Seções do Formulário de Orçamentos
    var clienteSecao = $('#clientes');
    function hideAllSections() {
        $('.form-section').hide();
    }
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
    $(medidasBtn).on('click', function() {
        showSection('medidas', medidasBtn, clienteBtn, prod_servBtn, adicionaisBtn, form_pgtoBtn);
    });
    $(clienteBtn).on('click', function() {
        showSection('clientes', clienteBtn, medidasBtn, prod_servBtn, adicionaisBtn, form_pgtoBtn);
    });
    $(prod_servBtn).on('click', function() {
        showSection('prod_serv', prod_servBtn, clienteBtn, medidasBtn, adicionaisBtn, form_pgtoBtn);
    });
    $(adicionaisBtn).on('click', function() {
        showSection('adicionais', adicionaisBtn, clienteBtn, medidasBtn, prod_servBtn, form_pgtoBtn);
    });
    $(form_pgtoBtn).on('click', function() {
        showSection('form_pgto', form_pgtoBtn, clienteBtn, medidasBtn, prod_servBtn, adicionaisBtn);
    });
    if ($('#medidas').length > 0) {
        showSection('medidas', medidasBtn, clienteBtn, prod_servBtn, adicionaisBtn, form_pgtoBtn);
    }
    if ($('#enderecos').length > 0) {
        showSection1('enderecos', endBt, compBt);
    }
    $(document).on('click', '#info-icon', function() {
        var orderId = $(this).data('id');
        listarOrdensServico(orderId);
    });
    $('#id_serial, #id_nome_empresa, #id_nome_emp, #id_desc_prod').focus();
    $('#loadingModal').modal({
        keyboard: true,
        backdrop: 'static'});
    $('#cliente, #id_cli').select2({
        placeholder: 'Selecione um cliente',
        allowClear: true,
        minimumInputLength: 1,
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        language: {
            inputTooShort: function() {
                return 'Por favor, insira 1 ou mais caracteres';
            },
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        },
        ajax: {
            url: '/clientes/lista_ajax/',
            dataType: 'json',
            delay: 250,
            data: function(params) {
                return { term: params.term };
            },
            processResults: function(data) {
                return {
                    results: data.clientes.map(function(cliente) {
                        return {
                            id: cliente.id,
                            text: cliente.fantasia
                        };
                    })
                };
            },
            cache: true
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#fornecedor, #id_forn, #id_fornecedor').select2({
        placeholder: 'Selecione um fornecedor',
        allowClear: true,
        minimumInputLength: 1,
        templateResult: function (data) {
            if (!data.id) {
                return data.text;
            }
            var $container = $(`
                <div style="display: flex; flex-direction: column; line-height: 1.2;">
                    <span style="font-size: 14px;">${data.id}</span><br>
                    <strong style="font-size: 14px;">${data.text}</strong>
                </div>
            `);
            return $container;
        },
        templateSelection: function (data) {
            return data.text;
        },
        language: {
            inputTooShort: function() {
                return 'Por favor, insira 1 ou mais caracteres';
            },
            noResults: function() {
                return 'Nenhum resultado encontrado';
            },
            searching: function() {
                return 'Procurando...';
            }
        },
        ajax: {
            url: '/fornecedores/lista_ajax/',
            dataType: 'json',
            delay: 250,
            data: function(params) {
                return { term: params.term };
            },
            processResults: function(data) {
                return {
                    results: data.fornecedores.map(function(fornecedor) {
                        return {
                            id: fornecedor.id,
                            text: fornecedor.fantasia
                        };
                    })
                };
            },
            cache: true
        }
    }).on('select2:open', function () {
        setTimeout(function() {
            document.querySelector('.select2-container--open .select2-search__field').focus();
        }, 50);
    });
    $('#id_unid_prod, #unid, #id_unidadeProduto').select2({
        placeholder: 'Selecione uma opção',
        allowClear: true
    });
    // Funções referentes aos formulários de cadastro e edição
    $('#createForm').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.returnValue=false;
            e.cancel = true;
            e.stopPropagation();
        }
    });
    $('.formularios').on('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
        }
    });
    function obterDataAtual2() {
        const dataAtual = new Date();
        const ano = dataAtual.getFullYear();
        let mes = (dataAtual.getMonth() + 1).toString().padStart(2, '0'); // Adiciona zero à esquerda, se necessário
        let dia = dataAtual.getDate().toString().padStart(2, '0'); // Adiciona zero à esquerda, se necessário
        return `${dia}/${mes}/${ano}`;}
    if ($('#id_dt_inicio, #id_dt_venc, #data, #id_dt_emi, #dt_efet_ent, #inpDtPriParc, #id_dt_ent, #id_data_aniversario, #id_data_emissao, #data_inicio1, #data_fim1, #id_data_doc, #id_data_prop, #id_dt_visita, #dtVisita, #id_dt_criacao').val() === "") {
        $('#id_dt_inicio, #id_dt_venc, #data, #id_dt_emi, #dt_efet_ent, #inpDtPriParc, #id_dt_ent, #id_data_aniversario, #id_data_emissao, #data_inicio1, #data_fim1, #id_data_doc, #id_data_prop, #id_dt_visita, #dtVisita, #id_dt_criacao').val(obterDataAtual2());
    }
    if ($('#id_qtd, #id_quantidade').val() === '') {
        $('#id_qtd, #id_quantidade').val('1.00');
    }
    if ($('#id_rolo').val() === '') {
        $('#id_rolo').val('0.60');
    }
    if ($('#id_qtd_mens, #id_qtd_parcelas').val() === '') {
        $('#id_qtd_mens, #id_qtd_parcelas').val('1');
    }
    if ($('#id_vl_mens, #id_valor_mensalidade, #id_preco_unit, #id_vl_prod').val() === '') {
        $('#id_vl_mens, #id_valor_mensalidade, #id_preco_unit, #id_vl_prod').val('0.00');
    }
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
    $('#id_cep_administrador, #id_cep').on('input', function(event) {
        cepFormatado(event);
    });
    const dataFormatada = (event) => {
        let input = event.target;
        input.value = dataMask(input.value);
    };
    const dataMask = (value) => {
        if (!value) return "";
        value = value.replace(/\D/g, ''); // Remove todos os caracteres não numéricos
        value = value.replace(/(\d{2})(\d)/, '$1/$2'); // Insere a primeira barra
        value = value.replace(/(\d{2})(\d)/, '$1/$2'); // Insere a segunda barra
        return value.substring(0, 10); // Limita o tamanho para 10 caracteres (dd/mm/aaaa)
    };
    $('#id_dt_inicio, #data, #id_dt_emi, #dt_efet_ent, #inpDtPriParc, #id_dt_ent, #id_dt_venc, #id_data_aniversario, #id_data_prop, #id_data_certificado, #id_data_nascimento, #id_data_nascimento_administrador, #data_inicio1, #data_fim1, #id_data_emissao, #id_data_entrega, #id_dt_criacao').on('input', function(event) {
        dataFormatada(event);
    });
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
    $('#id_data_realizacao, #data_inicio, #data_fim').on('input', function(event) {
        dataFormatada1(event);
    });
    let selectors = '.valor-prod, .valor-prod-adc, .qtd-prod-adc, .qtd-prod, #campo_1, #campo_2, #id_margem, #id_vl_prod, .inpFrete, #id_quantidade, #total-frete, .editable, #id_preco_unit, #id_valor_mensalidade, #id_vl_mens, #id_qtd, #id_m2, #id_acrescimo, #id_desconto, #id_vl_compra, #id_vl_compra_adc, #id_estoque_prod, #campo_desconto, #campo_acrescimo';
    $(selectors).each(function() {
        if (!$(this).val()) {
            $(this).val("0.00");
        }
    });
    function formatCurrency(input) {
        let value = input.value.replace(/\D/g, ''); // Remove todos os caracteres não numéricos
        let formattedValue = (parseFloat(value) / 100).toFixed(2) // Converte para float e formata com 2 casas decimais
                            .replace(',', '.') // Substitui ponto por vírgula
                            .replace(/\B(?=(\d{3})+(?!\d))/g, ''); // Adiciona pontos como separadores de milhar
        input.value = formattedValue;
    }
    $(selectors).on('input', function(event) {
        formatCurrency(event.target);
    });
    $(selectors).on('focus', function(event) {
        let input = event.target;
        if (input.value === "0.00") {
            input.value = "0.00";
        }
    });
    const campoData = $('#id_data_aniversario');
    const campoDataAniversario = $('#id_id_data_aniversario');
    campoData.on('input', function () {
        campoDataAniversario.val(campoData.val());});
    const dataPesquisaInput = $("#data_pesquisa");
    // Obtenha a data atual no formato correto para o campo de entrada de data
    const today = new Date().toISOString().slice(0, 10);
    // Defina o valor do campo de entrada para a data atual
    dataPesquisaInput.val(today);
});