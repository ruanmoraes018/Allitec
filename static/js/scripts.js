$(document).ready(function() {
    var form = $('#createForm');
    var cadastro = 'https://allitec.pythonanywhere.com/orcamentos/add/';
    calcTotalEntrada();
    $('.table').addClass("table-sm");
    $('[name^="nome_"]').first().focus();
    $('[name^="descricao"]').first().focus();
    // Novo teste
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
                Toastify({
                    text: "Status atualizado com sucesso!",
                    duration: 5000,
                    gravity: "top",
                    position: "center",
                    backgroundColor: "linear-gradient(to right, #00b09b, #96c93d)",
                    stopOnFocus: true,
                    escapeMarkup: false,
                }).showToast();
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
                Toastify({
                    text: "Erro ao atualizar o status!",
                    duration: 5000,
                    gravity: "top",
                    position: "center",
                    backgroundColor: "linear-gradient(to right, #ff416c, #ff4b2b)",
                    stopOnFocus: true,
                    escapeMarkup: false,
                }).showToast();
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
            Toastify({
                text: "Selecione ao menos um produto antes de continuar.",
                duration: 3000,
                close: true,
                gravity: "top", // top ou bottom
                position: "center", // left, center ou right
                backgroundColor: "#ffc107",
                stopOnFocus: true,
                escapeMarkup: false,
            }).showToast();
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
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Código deve ser informado!',
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                stopOnFocus: true,
                escapeMarkup: false,
            }).showToast();
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
                Toastify({
                    text: `<i class="fa-solid fa-triangle-exclamation"></i> O código "${cod}" já está incluso na listagem!`,
                    duration: 5000,
                    gravity: "top",
                    position: "center",
                    backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                    stopOnFocus: true,
                    escapeMarkup: false,
                }).showToast();
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
                alert("Erro ao buscar a tabela de preço");
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
                alert("Erro ao buscar a tabela de preço");
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
            Toastify({ text: 'Selecione uma tabela antes de adicionar!', duration: 5000, gravity: "top", position: "center", backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)', stopOnFocus: true }).showToast();
            return;
        }
        if (vl_p === "0.00" || vl_p === "" || vl_p === "0") {
            Toastify({ text: 'Preço de Venda deve ser informado!', duration: 5000, gravity: "top", position: "center", backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)', stopOnFocus: true }).showToast();
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
                Toastify({ text: `Tabela "${tabNome}" já está inclusa na listagem!`, duration: 5000, gravity: "top", position: "center", backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)', stopOnFocus: true }).showToast();
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
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Preço Unitário deve ser informado!',
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                stopOnFocus: true,
                escapeMarkup: false,
            }).showToast();
        } else if (trEditando) {
            // === Atualizar linha existente ===
            let idx = trEditando.data("id");
            trEditando.find("td:eq(0)").html(`${cod}
                <input type="hidden" name="produtos[${idx}][codigo]" value="${cod}">`);
            trEditando.find("td:eq(1)").html(`${prod}
                <input type="hidden" name="produtos[${idx}][produto]" value="${prod}">`);
            trEditando.find("td:eq(2)").html(`${qtd}
                <input type="hidden" name="produtos[${idx}][quantidade]" value="${qtd}">`);
            trEditando.find("td:eq(3)").html(`${preco}
                <input type="hidden" name="produtos[${idx}][preco_unitario]" value="${preco}">`);
            trEditando.find("td:eq(4)").html(`${dsct}
                <input type="hidden" name="produtos[${idx}][desconto]" value="${dsct}">`);
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
                Toastify({
                    text: `<i class="fa-solid fa-triangle-exclamation"></i> O código "${cod}" já está incluso na listagem!`,
                    duration: 5000,
                    gravity: "top",
                    position: "center",
                    backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                    stopOnFocus: true,
                    escapeMarkup: false,
                }).showToast();
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
                Toastify({
                    text: 'Erro ao buscar o produto. Tente novamente!',
                    duration: 5000,
                    gravity: "top",
                    position: "center",
                    backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                    stopOnFocus: true,
                    escapeMarkup: false,
                }).showToast();
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
                       <span class='visually-hidden'>Loading...</span></div>`,
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
                Toastify({
                    text: '<i class="fa-solid fa-hourglass-start"></i> Tempo expirado. A solicitação não foi respondida!',
                    duration: 6000,
                    close: true,
                    gravity: "top",
                    position: "center",
                    escapeMarkup: false, // Permite HTML no toast
                    style: {
                        background: "linear-gradient(to right, #343a40, #6c757d)",
                        color: "#fff",
                        borderRadius: "8px"
                    }
                }).showToast();
                return;
            }
            $.get(`/orcamentos/verificar-solicitacao/${solicitacaoId}/`, function(data) {
                if (data.status === 'Aprovada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    Toastify({
                        text: '<i class="fa-solid fa-circle-check"></i> Solicitação Concedida ao usuário!',
                        duration: 6000,
                        close: true,
                        gravity: "top",
                        position: "center",
                        escapeMarkup: false, // Permite HTML no toast
                        style: {
                            background: "linear-gradient(to right, #28a745, #218838)",
                            color: "#fff",
                            borderRadius: "8px"
                        }
                    }).showToast();
                    if (acaoSelecionada === "atribuir_desconto") {
                        $('#modalDesconto').modal('show');
                    } else if (acaoSelecionada === "atribuir_acrescimo") {
                        $('#modalAcrescimo').modal('show');
                    }
                } else if (data.status === 'Negada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    Toastify({
                        text: '<i class="fa-solid fa-circle-xmark"></i> Solicitação Negada ao usuário!',
                        duration: 6000,
                        close: true,
                        gravity: "top",
                        position: "center",
                        escapeMarkup: false, // Permite HTML no toast
                        style: {
                            background: "linear-gradient(to right, #dc3545, #c82333)",
                            color: "#fff",
                            borderRadius: "8px"
                        }
                    }).showToast();
                }
            });
        }, 5000);
    }
    $('#userSelectModal').on('show.bs.modal', function () {
        $.get('/orcamentos/usuarios-com-permissao/', function(data) {
            const select = $('#userSelect');
            select.empty();
            data.usuarios.forEach(u => {
                select.append(`<option selected value="">------</option>`);
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
            Toastify({
                text: '<i class="fa-solid fa-circle-exclamation"></i> ID da solicitação não encontrado!',
                duration: 6000,
                close: true,
                gravity: "top",
                position: "center",
                escapeMarkup: false, // Permite HTML no toast
                style: {
                    background: "linear-gradient(to right, #d58300, #ffc93b)",
                    color: "#fff",
                    borderRadius: "8px"
                }
            }).showToast();
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
                Toastify({
                    text: '<i class="fa-solid fa-circle-check"></i> Solicitação Concedida ao usuário!',
                    duration: 6000,
                    close: true,
                    gravity: "top",
                    position: "center",
                    escapeMarkup: false, // Permite HTML no toast
                    style: {
                        background: "linear-gradient(to right, #28a745, #218838)",
                        color: "#fff",
                        borderRadius: "8px"
                    }
                }).showToast();
            } else {
                Toastify({
                    text: '<i class="fa-solid fa-circle-xmark"></i> Solicitação Negada ao usuário!',
                    duration: 6000,
                    close: true,
                    gravity: "top",
                    position: "center",
                    escapeMarkup: false, // Permite HTML no toast
                    style: {
                        background: "linear-gradient(to right, #dc3545, #c82333)",
                        color: "#fff",
                        borderRadius: "8px"
                    }
                }).showToast();
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
                Toastify({
                    text: `<span style="display: flex; align-items: center; gap: 8px;">
                                <i class="fa-solid fa-exclamation"></i> ${msgNegado}
                           </span>`,
                    duration: 5000,
                    gravity: "top",
                    position: "center",
                    backgroundColor: "linear-gradient(to right, #02202B, #017AB1)",
                    stopOnFocus: true,
                    escapeMarkup: false,
                }).showToast();
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
    function atualizarTabela() {
        const tp_pintura = $('#id_tp_pintura').val();
        ['#itensTableProduto', '#itensTableProdutoAdc'].forEach(sel => {
            $(sel + ' tbody tr').each(function () {
                let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
                let qtd  = parseFloat($('#id_qtd').val().replace(',', '.')) || 1;
                let larg = parseFloat($('#id_larg').val().replace(',', '.')) || 0;
                let larg_c = parseFloat($('#id_larg_corte').val().replace(',', '.')) || 0;
                let alt  = parseFloat($('#id_alt').val().replace(',', '.')) || 0;
                let alt_c  = parseFloat($('#id_alt_corte').val().replace(',', '.')) || 0;
                let m2 = parseFloat($('#id_m2').val().replace(',', '.')) || 0;
                let compra = parseFloat($(this).find('td:nth-child(5)').text().replace(',', '.')) || 0;
                let venda  = parseFloat($(this).find('td:nth-child(6)').text().replace(',', '.')) || 0;
                let novaQtd = 1;
                if (desc.startsWith('GUIAS') || desc.startsWith('TUBO DE AFASTAMENTO')) novaQtd = qtd * (alt_c + 0.2) * 2;
                else if (desc.startsWith('EIXO') || desc.startsWith('SOLEIRA')) novaQtd = qtd * larg_c;
                else if (desc.startsWith('PERFIL DESLIZANTE')) novaQtd = alt_c * 4;
                else if (desc.startsWith('TRAVA LÂMINA')) novaQtd = alt * 10;
                else if (desc.startsWith('LÂMINAS LISAS')) novaQtd = m2;
                else if (desc.startsWith('LÂMINAS TRANSVISION')) novaQtd = m2;
                else if ((tp_pintura === "Eletrostática" && desc.startsWith('PINTURA ELETROSTÁTICA')) || (tp_pintura === "Automotiva" && desc.startsWith('PINTURA AUTOMOTIVA'))) novaQtd = m2;
                else if (desc.startsWith('MOTOR') || desc.startsWith('TRANSPORTE') || desc.startsWith('MÃO DE OBRA')) novaQtd = 1;
                else if (desc.startsWith('PORTINHOLA') || desc.startsWith('AÇALPÃO') || desc.startsWith('COLUNA REMOVIVEL')) novaQtd = 0;

                let compraTot = (compra * novaQtd).toFixed(2);
                let vendaTot  = (venda * novaQtd).toFixed(2);

                $(this).find('td:nth-child(7)').text(novaQtd.toFixed(2));
                $(this).find('td:nth-child(8)').text(compraTot);
                $(this).find('td:nth-child(9)').text(vendaTot);
            });
        });
        atualizarSubtotal();
    }
    let toastErrorShown = false;
    $('#id_pintura').on('change', function () {
        const temPintura = $(this).val();
        if (temPintura === 'Não') {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Campo Pintura está selecionado como Não, para inserir o produto, altere a opção para Sim!',
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                stopOnFocus: true,
                escapeMarkup: false,
            }).showToast();
            // 🔄 Primeiro atualiza tudo
            atualizarSubtotal();
            atualizarTabela();
            // ⌛ Depois de tudo pronto, esconde o loading
            setTimeout(() => {
                finalizarLoading();
            }, 500); // leve delay evita bug do mobile
        } else {
            atualizarSubtotal();
            atualizarTabela();
            setTimeout(() => {
                finalizarLoading();
            }, 500);
        }
    });
    toastErrorShown = false;
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
        } else {
            resultado = (alt_corte - 0.6) / 7.5;
        }
        let final = arredondarParaCima(resultado, 2) * 100;
        $(`.ft-peso[data-porta="${porta}"]`).val(final.toFixed(2));
    }
    $(document).on('input', '.alt', function () {
        let porta = $(this).data('porta');
        $(`.alt-corte[data-porta="${porta}"]`).val($(this).val());
    });
    $('#id_tp_vao').val('Fora do Vão');
    function finalizarLoading() {
        setTimeout(() => {
            $("#loadingModal").modal("hide");
        }, 1500);
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
        } else {
            calc = larg - 0.08;
        }
        if (tp_vao === '1 Lado Dentro do Vão') {
            calc = larg + 0.03;
        }
        return calc.toFixed(2);
    }
    function atualizarLarguraCorte(porta) {
        const result = calcLgCorte(porta);
        $(`.larg-corte[data-porta="${porta}"]`).val(result);
        let ft_p = $(`.ft-peso[data-porta="${porta}"]`).val();
        ft_p = ft_p ? parseFloat(ft_p.replace(',', '.')) : 0;
        const calculo = (result * 0.8) * ft_p * 1.2;
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
    let motorCtrl = {};
    function buscarMotorIdeal(porta) {
        const peso = parseFloat($(`.peso[data-porta="${porta}"]`).val()) || 0;
        const altura = parseFloat($(`.alt[data-porta="${porta}"]`).val()) || 0;  // supondo que você tenha um campo de altura
        if (peso < 1) return;
        if (!motorCtrl[porta]) {
            motorCtrl[porta] = {
                ultimoMotor: null,
                ultimoPeso: null,
                inserir: false,
                ultimaAltura: null // armazenar a última altura
            };
        }
        const ranges = [150, 250, 350, 450, 550, 650, 750, 1000];
        const modelos = ["200KG", "300KG", "400KG", "500KG", "600KG", "700KG", "800KG", "1000KG"];
        const idx = ranges.findIndex(r => peso <= r);
        const motorNome = `MOTOR ${modelos[idx] || "1500KG"}`;
        const ctrl = motorCtrl[porta];
        if (ctrl.inserido && peso === ctrl.ultimoPeso && motorNome === ctrl.ultimoMotor && altura === ctrl.ultimaAltura) {
            return; // Não faz nada se nada mudou
        }
        removerProdutoMotor(porta);
        $.get('/produtos/lista_ajax/', {
            s: motorNome,
            filtro: 'desc',
            tp_prod: 'Principal'
        })
        .done(res => {
            const p = res.produtos?.[0];
            if (!p) return;
            if (verificarProdutoMotor(porta, p.desc_prod)) return;
            setTimeout(() => {
                const $tbody = $(`#tblProd_${porta} tbody`);
                const linha = $tbody.find('tr').length + 1; // ✅ numeração correta
                $tbody.append(`
                    <tr data-porta="${porta}" data-item-id="${p.id}">
                        <td data-label="#" class="mobile-2col">${linha}</td>
                        <td data-label="Cód:" class="mobile-2col">${p.id}</td>
                        <td data-label="Desc.:" class="mobile-2col">${p.desc_prod}</td>
                        <td data-label="Unid:" class="mobile-2col">${p.unidProd}</td>
                        <td class="text-danger fw-bold mobile-3col" data-label="Vl. Compra:">${p.vl_compra}</td>
                        <td class="vl-unit text-success fw-bold mobile-3col" data-label="Vl. Unit:">${p.vl_prod}</td>
                        <td class="qtd-produto mobile-3col" data-label="Qtde:">1.00</td>
                        <td class="tot-compra text-danger fw-bold mobile-3col" data-label="Tot. Compra:">0.00</td>
                        <td class="vl-total text-success fw-bold mobile-3col" data-label="Vl. Total:">0.00</td>
                        <td data-label="Ações:" class="mobile-3col">
                            <i class="fas fa-edit editBtn" style="color: #13c43f; cursor:pointer;" data-bs-toggle="modal" data-bs-target="#editItemModal"></i>
                            <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor:pointer;"></i>
                        </td>
                    </tr>
                `);
                calcularEixoMotor(porta);
                atualizarTabelaPorta(porta);
                atualizarSubtotal();
                ctrl.ultimoPeso  = peso;
                ctrl.ultimoMotor = motorNome;
                ctrl.ultimaAltura = altura; // Atualiza a altura registrada
                ctrl.inserido    = true;
                atualizarJSONPortas(); // 👈 GARANTE que o motor entre
            }, 500);
        })
        .fail(() => {
            Toastify({
                text: 'Erro ao buscar motor ideal.',
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: 'linear-gradient(to right, #db1e47, #ff7373)'
            }).showToast();
        });
    }
    function removerProdutoMotor(porta) {
        $(`#tblProd_${porta} tbody tr`).each(function () {
            const desc = $(this).find('td:eq(2)').text().toLowerCase().trim();
            if (desc.startsWith('motor')) {
                $(this).remove();
            }
        });
        if (motorCtrl[porta]) {
            motorCtrl[porta].inserido = false;
        }
    }
    function verificarProdutoMotor(porta, nome) {
        const nomeBusca = nome.toLowerCase().trim();
        let existe = false;
        $(`#tblProd_${porta} tbody tr`).each(function () {
            const desc = $(this).find('td:eq(2)').text().toLowerCase().trim();
            if (desc === nomeBusca) {
                existe = true;
            }
        });
        return existe;
    }
    function resetarControleMotor() {
        motorCtrl = {};
    }
    function verificarPintura(porta) {
        const temPintura = $("#id_pintura").val();
        const tp_pintura = $("#id_tp_pintura").val();
        const $tbody = $(`#tblAdc_${porta} tbody`);
        if (temPintura === "Não") {
            $tbody.find('tr').each(function () {
                const desc = $(this).find('td:nth-child(3)').text().toUpperCase();
                if (desc.includes("PINTURA")) {
                    $(this).remove();
                }
            });
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            return;
        }
        const pinturaCorreta =
            tp_pintura === "Eletrostática"
                ? "PINTURA ELETROSTÁTICA"
                : "PINTURA AUTOMOTIVA";
        const pinturaErrada =
            tp_pintura === "Eletrostática"
                ? "PINTURA AUTOMOTIVA"
                : "PINTURA ELETROSTÁTICA";
        $tbody.find('tr').each(function () {
            const desc = $(this).find('td:nth-child(3)').text().toUpperCase();
            if (desc === pinturaErrada) {
                $(this).remove();
            }
        });
        let existe = false;
        $tbody.find('tr').each(function () {
            const desc = $(this).find('td:nth-child(3)').text().toUpperCase();
            if (desc === pinturaCorreta) {
                existe = true;
            }
        });
        if (existe) {
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            return;
        }
        $.get('/produtos/lista_ajax/', {
            tp: 'desc',
            tp_prod: 'Adicional',
            s: pinturaCorreta
        })
        .done(resp => {
            const p = resp.produtos?.find(
                prod => prod.desc_prod.toUpperCase() === pinturaCorreta
            );
            if (!p) return;
            const linha = $tbody.find('tr').length + 1;
            $tbody.append(`
                <tr data-porta="${porta}" data-item-id="${p.id}">
                    <td data-label="#" class="mobile-2col">${linha}</td>
                    <td data-label="Cód:" class="mobile-2col">${p.id}</td>
                    <td data-label="Desc.:" class="mobile-2col">${p.desc_prod}</td>
                    <td data-label="Unid:" class="mobile-2col">${p.unidProd}</td>
                    <td class="text-danger fw-bold mobile-3col" data-label="Vl. Compra:">${p.vl_compra}</td>
                    <td class="vl-unit text-success fw-bold mobile-3col" data-label="Vl. Unit:">${p.vl_prod}</td>
                    <td class="qtd-produto mobile-3col" data-label="Qtde:">0</td>
                    <td class="tot-compra text-danger fw-bold mobile-3col" data-label="Tot. Compra:">0.00</td>
                    <td class="vl-total text-success fw-bold mobile-3col" data-label="Vl. Total:">0.00</td>
                    <td data-label="Ações:" class="mobile-3col">
                        <i class="fas fa-edit editBtn" data-bs-toggle="modal" data-bs-target="#editItemAdcModal" style="color: #13c43f; cursor: pointer;"></i>
                        <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor: pointer;"></i>
                    </td>
                </tr>
            `);
            // 🔥 AGORA SIM A QUANTIDADE VAI SER m2
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
        });
    }
    function atualizarPinturaPorta(porta) {
        const temPintura = $('#id_pintura').val();       // Sim / Não
        const tpPintura  = $('#id_tp_pintura').val();    // Eletrostática / Automotiva
        const $tabela = $(`#tblAdc_${porta} tbody`);
        if (!$tabela.length) return;
        const m2 = parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;
        const DESC_ELET = 'PINTURA ELETROSTÁTICA';
        const DESC_AUTO = 'PINTURA AUTOMOTIVA';
        $tabela.find('tr').each(function () {
            const desc = $(this).find('td:eq(2)').text().toUpperCase().trim();
            if (desc === DESC_ELET || desc === DESC_AUTO) {
                $(this).remove();
            }
        });
        if (temPintura === 'Não') {
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            return;
        }
        const pinturaCorreta = tpPintura === 'Automotiva'
            ? DESC_AUTO
            : DESC_ELET;
        $.get('/produtos/lista_ajax/', {
            s: pinturaCorreta,
            filtro: 'desc',
            tp_prod: 'Adicional'
        })
        .done(res => {
            const p = res.produtos?.[0];
            if (!p) return;
            const jaExiste = $tabela.find('tr').filter(function () {
                return $(this).find('td:eq(2)').text().toUpperCase().trim() === pinturaCorreta;
            }).length > 0;
            if (jaExiste) return;
            const idx = $tabela.find('tr').length + 1;
            $tabela.append(`
                <tr data-porta="${porta}" data-item-id="${p.id}">
                    <td data-label="#" class="mobile-2col">${idx+1}</td>
                    <td data-label="Cód:" class="mobile-2col">${p.id}</td>
                    <td data-label="Desc.:" class="mobile-2col">${p.desc_prod}</td>
                    <td data-label="Unid:" class="mobile-2col">${p.unidProd}</td>
                    <td class="text-danger fw-bold mobile-3col" data-label="Vl. Compra:">${p.vl_compra}</td>
                    <td class="vl-unit text-success fw-bold mobile-3col" data-label="Vl. Unit:">${p.vl_prod}</td>
                    <td class="qtd-produto mobile-3col" data-label="Qtde:">${m2.toFixed(2)}</td>
                    <td class="tot-compra text-danger fw-bold mobile-3col" data-label="Tot. Compra:">0.00</td>
                    <td class="vl-total text-success fw-bold mobile-3col" data-label="Vl. Total:">0.00</td>
                    <td data-label="Ações:" class="mobile-3col">
                        <i class="fas fa-edit editBtn" style="color: #13c43f; cursor: pointer;" data-bs-toggle="modal" data-bs-target="#editItemAdcModal"></i>
                        <i class="fas fa-trash deleteBtn" style="color:#db1e47;cursor:pointer"></i>
                    </td>
                </tr>
            `);
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
        })
        .fail(() => {
            Toastify({
                text: 'Erro ao buscar pintura.',
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: 'linear-gradient(to right, #db1e47, #ff7373)'
            }).showToast();
        });
    }
    $('#id_pintura').on('change', function () {
        $('.porta-container').each(function () {
            const porta = $(this).data('porta');
            atualizarPinturaPorta(porta);
            setTimeout(() => {
                finalizarLoading();
            }, 500);
        });
    });
    function atualizarLaminarPorta(porta) {
        const tpLam = $(`.tipo-lamina[data-porta="${porta}"]`).val(); // Fechada / Transvision
        const $tabela = $(`#tblProd_${porta} tbody`);
        if (!$tabela.length) return;
        const m2 = parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;
        // descrições padronizadas
        const DESC_LISA  = 'LÂMINAS LISAS';
        const DESC_TRANS = 'LÂMINAS TRANSVISION';
        // remove qualquer lâmina existente
        $tabela.find('tr').each(function () {
            const desc = $(this).find('td:eq(2)').text().toUpperCase().trim();
            if (desc === DESC_LISA || desc === DESC_TRANS) {
                $(this).remove();
            }
        });
        // define qual lâmina deve entrar
        const laminaCorreta = tpLam === 'Transvision'
            ? DESC_TRANS
            : DESC_LISA;
        // busca produto correto
        $.get('/produtos/lista_ajax/', {
            s: laminaCorreta,
            filtro: 'desc',
            tp_prod: 'Principal'
        })
        .done(res => {
            const p = res.produtos?.[0];
            if (!p) return;
            // segurança extra contra duplicação
            const jaExiste = $tabela.find('tr').filter(function () {
                return $(this).find('td:eq(2)').text().toUpperCase().trim() === laminaCorreta;
            }).length > 0;
            if (jaExiste) return;
            // próxima numeração correta
            const idx = $tabela.find('tr').length + 1;
            // insere a lâmina correta
            $tabela.append(`
                <tr data-porta="${porta}">
                    <td data-label="#" class="mobile-2col">${idx}</td>
                    <td data-label="Cód:" class="mobile-2col">${p.id}</td>
                    <td data-label="Desc.:" class="mobile-2col">${p.desc_prod}</td>
                    <td data-label="Unid:" class="mobile-2col">${p.unidProd}</td>
                    <td class="text-danger fw-bold mobile-3col" data-label="Vl. Compra:">${p.vl_compra}</td>
                    <td class="vl-unit text-success fw-bold mobile-3col" data-label="Vl. Unit:">${p.vl_prod}</td>
                    <td class="qtd-produto mobile-3col" data-label="Qtde:">${m2.toFixed(2)}</td>
                    <td class="tot-compra text-danger fw-bold mobile-3col" data-label="Tot. Compra:">0.00</td>
                    <td class="vl-total text-success fw-bold mobile-3col" data-label="Vl. Total:">0.00</td>
                    <td data-label="Ações:" class="mobile-3col">
                        <i class="fas fa-edit editBtn" style="color: #13c43f; cursor: pointer;" data-bs-toggle="modal" data-bs-target="#editItemModal"></i>
                        <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor:pointer;"></i>
                    </td>
                </tr>
            `);
            // recalcula totais
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
        })
        .fail(() => {
            Toastify({
                text: 'Erro ao buscar lâminas.',
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: 'linear-gradient(to right, #db1e47, #ff7373)'
            }).showToast();
        });
    }
    $(document).on('change', '.tipo-lamina', function () {
        const porta = $(this).data('porta');
        const larg = $(`.larg[data-porta="${porta}"]`).val().trim();
        const alt  = $(`.alt[data-porta="${porta}"]`).val().trim();
        buscarProdutosPrincipais(porta, larg, alt);
        atualizarTabelaPorta(porta);
        atualizarSubtotal();
        setTimeout(() => {
            finalizarLoading();
        }, 500);
    });
    $(document).on('keyup change', '.larg', function () {
        let porta = $(this).data('porta');
        atualizarLarguraCorte(porta);
    });
    $(document).on('change', '.tipo-vao', function () {
        let porta = $(this).data('porta');
        atualizarLarguraCorte(porta);
    });
    $('#id_tp_pintura').on('change', function () {
        $('.porta-container').each(function () {
            const porta = $(this).data('porta');
            atualizarPinturaPorta(porta);
        });
    });
    $("#prod_servBtn, #adicionaisBtn, #form_pgtoBtn").on("click", function () {
        atualizarSubtotal();
        calcularValorForma();
        somaFormas();
        console.log('Chamou aqui');
        atualizarJSONPortas();
        gerarJSONFormas();
    });
    atualizarJSONPortas();
    gerarJSONFormas();
    $("#id_tp_pintura, #id_pintura").change(function () {
        const porta = $(this).data("porta");
        $("#loadingModal").modal("show");
        verificarPintura(porta);
    });
    let debounceTimeout;
    function atualizarCalculoCompletoDebounced() {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            calcFtPeso();
            // calcularValor();
        }, 200);
    }
    $('#id_alt, #id_tp_vao, #id_larg, #id_qtd, #id_rolo, #id_alt_corte, #id_larg_corte').on('blur', atualizarCalculoCompletoDebounced);
    $('#id_desconto, #id_acrescimo').mask('000,000,000,000,000.00', {reverse: true});
    $('#desconto, #acrescimo').mask('000.000.000.000.000,00', {reverse: true});
    $('#id_vl_prod, #id_vl_prod_adc, #editValorItemInput, #editValorItemAdcInput, .editable, .inpFrete, #id_vl_form_pgto').mask('0000.00', {reverse: true});
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
            let vl_p_s = parseFloat($('#id_vl_p_s').val()) || 0;
            $('[id^="tblProd_"] tbody tr, [id^="tblAdc_"] tbody tr').each(function () {
                const compra = parseFloat(
                    $(this).find('.tot-compra').text().replace(',', '.')
                ) || 0;
                const venda = parseFloat(
                    $(this).find('.vl-total').text().replace(',', '.')
                ) || 0;
                custoTotal += compra;
                subtotal   += venda;
            });
            subtotal += vl_p_s;
            $('#custoTotal_txt').text(
                'R$ ' + custoTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
            );
            $('#subtotal_txt').text(
                'R$ ' + subtotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
            );
            $('#id_subtotal').val(subtotal.toFixed(2));
            $('#id_vl_form_pgto').val(subtotal.toFixed(2));
            const descontoRaw = $('#id_desconto').length
                ? $('#id_desconto').val()
                : '0';
            const acrescimoRaw = $('#id_acrescimo').length
                ? $('#id_acrescimo').val()
                : '0';
            const desconto = parseFloat(
                String(descontoRaw).replace(',', '.')
            ) || 0;
            const acrescimo = parseFloat(
                String(acrescimoRaw).replace(',', '.')
            ) || 0;
            const total = subtotal - desconto + acrescimo;
            $('#desconto').text('R$ ' + desconto.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
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
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Informe uma quantidade válida de Portas!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
            return;
        }
        resetarControleMotor();
        $("#tabelaPortasResumo tbody").empty();
        $("#accordionProdutos").empty();
        $("#accordionAdicionais").empty();
        for (let i = 1; i <= qtd; i++) {
            $("#tabelaPortasResumo tbody").append(`
                <tr id="linha_resumo_${i}" class="linha-porta" data-porta="${i}">
                    <td data-label="Porta:" class="num-porta mobile-3col">${i}</td>
                    <td data-label="Larg.:" class="mobile-3col"><input type="text" class="form-control form-control-sm larg" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Alt.:" class="mobile-3col"><input type="text" class="form-control form-control-sm alt" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Lg. Corte:" class="mobile-3col"><input readonly class="form-control form-control-sm larg-corte" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="At. Corte:" class="mobile-3col"><input readonly class="form-control form-control-sm alt-corte" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Qtd. Lâm.:" class="mobile-3col"><input readonly class="form-control form-control-sm qtd-laminas" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="M²:" class="mobile-3col"><input readonly class="form-control form-control-sm m2" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Ft. Peso:" class="mobile-3col"><input readonly class="form-control form-control-sm ft-peso" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Peso:" class="mobile-3col"><input readonly class="form-control form-control-sm peso" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Eix. Mot.:" class="mobile-3col"><input readonly class="form-control form-control-sm eix-mot" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Rolo:" class="mobile-3col"><input readonly class="form-control form-control-sm rolo" data-porta="${i}" placeholder="0.00"></td>
                    <td data-label="Tp. Lâm.:" class="mobile-3col">
                        <select class="form-select form-select-sm tipo-lamina" data-porta="${i}">
                            <option value="Fechada">Fechada</option>
                            <option value="Transvision">Transvision</option>
                        </select>
                    </td>
                    <td data-label="Tp. Vão:" class="mobile-2col">
                        <select class="form-select form-select-sm tipo-vao" data-porta="${i}">
                            <option value="Fora do Vão">Fora do Vão</option>
                            <option value="Dentro do Vão">Dentro do Vão</option>
                            <option value="1 Lado Dentro do Vão">1 Lado Dentro do Vão</option>
                        </select>
                    </td>
                    <td data-label="Exc.:" class="text-center mobile-2col">
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
        aplicarMascaras();
    }
    function aplicarMascaras() {
        $('.larg, .alt, .id_larg, .larg-corte, .alt-corte, .qtd-laminas, .m2, .ft-peso, .peso')
            .mask('000,000.00', { reverse: true });
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
                    <table class="table table-bordered table-sm table-striped tabela-produtos"
                        id="tblProd_${num}">
                        <thead class="table-dark">
                            <tr>
                                <th>#</th>
                                <th>Cód.</th>
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
                    <table class="table table-bordered table-sm table-striped tabela-adicionais"
                        id="tblAdc_${num}">
                        <thead class="table-dark">
                            <tr>
                                <th>#</th>
                                <th>Cód.</th>
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
    $(document).on("blur", ".alt", function () {
        const porta = $(this).data("porta");
        const largura = parseFloat($(`.larg[data-porta="${porta}"]`).val()) || 0;
        const altura = parseFloat($(`.alt[data-porta="${porta}"]`).val()) || 0;
        // Verifica se largura e altura são válidas
        if (!largura || !altura) return;
        // Verificações e cálculos relativos aos produtos
        buscarProdutosPrincipais(porta, largura, altura);
        buscarProdutosAdicionais(porta, largura, altura);
        verificarPintura(porta);
        atualizarLaminarPorta(porta);
        setTimeout(() => {
            atualizarPinturaPorta(porta);
        }, 500);
        // Calculos relacionados ao motor
        $("#loadingModal").modal("show");
        calcFtPeso(porta);
        atualizarLarguraCorte(porta);
        calcularEixoMotor(porta);
        calcM2(porta);
        atualizarLaminarPorta(porta);
        calcQtdLam(porta);
        // buscarMotorIdeal(porta);  // Chama a função para buscar o motor ideal
        setTimeout(() => {
            finalizarLoading();
        }, 500);
    });
    $(document).on("click", ".removerPorta", function () {
        const porta = $(this).data("porta");
        $("#linha_resumo_" + porta).remove();
        $("#accProd_" + porta).remove();
        $("#accAdc_" + porta).remove();
        reindexarPortas();
        aplicarMascaras();
    });
    $(document).on('click', '.deleteBtn', function() {
        // Remove a linha correspondente na tabela correta
        $(this).closest('tr').remove();
        atualizarSubtotal();
    });
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
    function atualizarTabelaPorta(porta) {
        const tp_pintura = $('#id_tp_pintura').val();
        const qtd = 1;
        const larg   = parseFloat($(`.larg[data-porta="${porta}"]`).val()) || 0;
        const larg_c = parseFloat($(`.larg-corte[data-porta="${porta}"]`).val()) || 0;
        const alt    = parseFloat($(`.alt[data-porta="${porta}"]`).val()) || 0;
        const alt_c  = parseFloat($(`.alt-corte[data-porta="${porta}"]`).val()) || 0;
        const m2     = parseFloat($(`.m2[data-porta="${porta}"]`).val()) || 0;
        let totalCompraProd = 0;
        let totalVendaProd  = 0;
        let totalCompraAdc  = 0;
        let totalVendaAdc   = 0;
        $(`#tblProd_${porta} tbody tr`).each(function () {
            const $tr = $(this);
            const desc   = $tr.find('td:eq(2)').text().toUpperCase().trim();
            const compra = parseFloat($tr.find('td:eq(4)').text().replace(',', '.')) || 0;
            const venda  = parseFloat($tr.find('.vl-unit').text().replace(',', '.')) || 0;
            let qtdCalc = 0;
            if (desc.startsWith('GUIAS') || desc.startsWith('TUBO DE AFASTAMENTO'))
                qtdCalc = qtd * (alt_c + 0.2) * 2;
            else if (desc.startsWith('EIXO') || desc.startsWith('SOLEIRA'))
                qtdCalc = qtd * larg_c;
            else if (desc.startsWith('PERFIL DESLIZANTE'))
                qtdCalc = alt_c * 4;
            else if (desc.startsWith('TRAVA LÂMINA'))
                qtdCalc = alt * 10;
            else if (desc.startsWith('LÂMINAS LISAS') || desc.startsWith('LÂMINAS TRANSVISION'))
                qtdCalc = m2;
            else if (desc.startsWith('MOTOR'))
                qtdCalc = 1;
            else
                qtdCalc = 0;
            const totCompra = compra * qtdCalc;
            const totVenda  = venda  * qtdCalc;
            $tr.find('.qtd-produto').text(qtdCalc.toFixed(2));
            $tr.find('.tot-compra').text(totCompra.toFixed(2));
            $tr.find('.vl-total').text(totVenda.toFixed(2));
            totalCompraProd += totCompra;
            totalVendaProd  += totVenda;
        });
        $(`#tblAdc_${porta} tbody tr`).each(function () {
            const $tr = $(this);
            const desc   = $tr.find('td:eq(2)').text().toUpperCase().trim();
            const compra = parseFloat($tr.find('td:eq(4)').text().replace(',', '.')) || 0;
            const venda  = parseFloat($tr.find('.vl-unit').text().replace(',', '.')) || 0;
            let qtdCalc = 0;
            if (
                (tp_pintura === "Eletrostática" && desc.startsWith("PINTURA ELETROSTÁTICA")) ||
                (tp_pintura === "Automotiva" && desc.startsWith("PINTURA AUTOMOTIVA"))
            ) {
                qtdCalc = m2;
            }
            else if (
                desc.startsWith('TRANSPORTE') ||
                desc.startsWith('MÃO DE OBRA')
            )
                qtdCalc = 1;
            else
                qtdCalc = 0;
            const totCompra = compra * qtdCalc;
            const totVenda  = venda  * qtdCalc;
            $tr.find('.qtd-produto').text(qtdCalc.toFixed(2));
            $tr.find('.tot-compra').text(totCompra.toFixed(2));
            $tr.find('.vl-total').text(totVenda.toFixed(2));
            totalCompraAdc += totCompra;
            totalVendaAdc  += totVenda;
        });
        $(`#totCompra_porta_${porta}`).text("R$ " +
            totalCompraProd.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        );
        $(`#totVenda_porta_${porta}`).text("R$ " +
            totalVendaProd.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        );
        $(`#totCompraAdc_porta_${porta}`).text("R$ " +
            totalCompraAdc.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        );
        $(`#totVendaAdc_porta_${porta}`).text("R$ " +
            totalVendaAdc.toLocaleString('pt-BR', { minimumFractionDigits: 2 })
        );
    }
    const medidasCtrl = {};
    function buscarProdutosPrincipais(num, lg, at) {
        medidasCtrl[num] ??= { larg: null, alt: null };
        prodManager.data[Number(num)] ??= [];
        const ctrl = medidasCtrl[num];
        if (ctrl.larg === lg && ctrl.alt === at) return;
        ctrl.larg = lg;
        ctrl.alt = at;
        const tpLamina = $(`.tipo-lamina[data-porta="${num}"]`).val();
        const $tbody = $("#tblProd_" + num + " tbody");
        $.get('/produtos/lista_ajax/', { tp: "desc", tp_prod: "Principal" }, function (resp) {
            $tbody.empty();
            let contador = 1;
            resp.produtos.forEach((p) => {
                const desc = p.desc_prod.toUpperCase();
                if (desc.includes("MOTOR")) return;
                if (desc.includes("LÂMINAS")) {
                    if (tpLamina === "Fechada" && desc.includes("TRANSVISION")) return;
                    if (tpLamina === "Transvision" && desc.includes("LISAS")) return;
                }
                prodManager.data[Number(num)].push({
                    id: p.id,                    // 👈 IMPORTANTE
                    cod: p.id,
                    desc: p.desc_prod,
                    unid: p.unidProd,
                    vl_compra: parseFloat(p.vl_compra),
                    vl_unit: parseFloat(p.vl_prod),
                    qtd: 0,
                    total: 0
                });
                $tbody.append(`
                    <tr data-porta="${num}" data-item-id="${p.id}">
                        <td data-label="#" class="mobile-2col">${contador}</td>
                        <td data-label="Cód:" class="mobile-2col">${p.id}</td>
                        <td data-label="Desc.:" class="mobile-2col">${p.desc_prod}</td>
                        <td data-label="Unid:" class="mobile-2col">${p.unidProd}</td>
                        <td class="text-danger fw-bold mobile-3col" data-label="Vl. Compra:">${p.vl_compra}</td>
                        <td class="vl-unit text-success fw-bold mobile-3col" data-label="Vl. Unit:">${p.vl_prod}</td>
                        <td class="qtd-produto mobile-3col" data-label="Qtde:">0.00</td>
                        <td class="tot-compra text-danger fw-bold mobile-3col" data-label="Tot. Compra:">0.00</td>
                        <td class="vl-total text-success fw-bold mobile-3col" data-label="Vl. Total:">0.00</td>
                        <td data-label="Ações:" class="mobile-3col">
                            <i class="fas fa-edit editBtn" style="color: #13c43f; cursor: pointer;" data-bs-toggle="modal" data-bs-target="#editItemModal"></i>
                            <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor: pointer;"></i>
                        </td>
                    </tr>
                `);
                contador++;
            });
            buscarMotorIdeal(num, lg, at);
            atualizarJSONPortas();
            atualizarTabelaPorta(num);
        });
    }
    function buscarProdutosAdicionais(porta) {
        prodAdcManager.data[Number(porta)] ??= [];
        $.get('/produtos/lista_ajax/', {
            tp: "desc",
            tp_prod: "Adicional"
        }, function (resp) {
            const tabela = $(`#tblAdc_${porta} tbody`).empty();
            let contador = 1;
            resp.produtos.forEach((p) => {
                prodAdcManager.data[Number(porta)].push({
                    id: p.id,                    // 👈 IMPORTANTE
                    cod: p.id,
                    desc: p.desc_prod,
                    unid: p.unidProd,
                    vl_compra: parseFloat(p.vl_compra),
                    vl_unit: parseFloat(p.vl_prod),
                    qtd: 0,
                    total: 0
                });
                tabela.append(`
                    <tr data-porta="${porta}" data-item-id="${p.id}">
                        <td data-label="#" class="mobile-2col">${contador}</td>
                        <td data-label="Cód:" class="mobile-2col">${p.id}</td>
                        <td data-label="Desc.:" class="mobile-2col">${p.desc_prod}</td>
                        <td data-label="Unid:" class="mobile-2col">${p.unidProd}</td>
                        <td class="text-danger fw-bold mobile-3col" data-label="Vl. Compra:">${p.vl_compra}</td>
                        <td class="vl-unit text-success fw-bold mobile-3col" data-label="Vl. Unit:">${p.vl_prod}</td>
                        <td class="qtd-produto mobile-3col" data-label="Qtde:">0</td>
                        <td class="tot-compra text-danger fw-bold mobile-3col" data-label="Tot. Compra:">0.00</td>
                        <td class="vl-total text-success fw-bold mobile-3col" data-label="Vl. Total:">0.00</td>
                        <td data-label="Ações:" class="mobile-3col">
                            <i class="fas fa-edit editBtn" data-bs-toggle="modal" data-bs-target="#editItemAdcModal" style="color: #13c43f; cursor: pointer;"></i>
                            <i class="fas fa-trash deleteBtn" style="color: #db1e47; cursor: pointer;"></i>
                        </td>
                    </tr>
                `);
                contador++;
            });
            verificarPintura(porta);
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            atualizarJSONPortas();
        });
    }
    function atualizarJSONPortas() {
        let portas = [];
        console.log("=== INICIANDO atualizarJSONPortas ===");
        $(".linha-porta").each(function () {
            const $linha = $(this);
            const portaNum = parseInt($linha.data("porta"));
            console.log("Processando porta:", portaNum);
            let dadosPorta = {
                numero: portaNum,
                largura: parseFloat($(`.larg[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                altura: parseFloat($(`.alt[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                qtd_lam: parseFloat($(`.qtd-laminas[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                m2: parseFloat($(`.m2[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                larg_corte: parseFloat($(`.larg-corte[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                alt_corte: parseFloat($(`.alt-corte[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                rolo: parseFloat($(`.rolo[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                peso: parseFloat($(`.peso[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                ft_peso: parseFloat($(`.ft-peso[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                eix_mot: parseFloat($(`.eix-mot[data-porta="${portaNum}"]`).val().replace(',', '.')) || 0,
                tipo_lamina: $(`.tipo-lamina[data-porta="${portaNum}"]`).val(),
                tipo_vao: $(`.tipo-vao[data-porta="${portaNum}"]`).val(),
                produtos: [],
                adicionais: []
            };
            $(`#tblProd_${portaNum} tbody tr`).each(function () {
                const $tr = $(this);
                const codProd = $tr.find("td:eq(1)").text().trim();
                const qtd = parseFloat($tr.find(".qtd-produto").text().trim()) || 0;
                if (codProd) {
                    dadosPorta.produtos.push({
                        codProd: codProd,
                        qtdProd: qtd // pode ser 0
                    });
                }
            });
            $(`#tblAdc_${portaNum} tbody tr`).each(function () {
                const $tr = $(this);
                const codProd = $tr.find("td:eq(1)").text().trim();
                const qtd = parseFloat($tr.find(".qtd-produto").text().trim()) || 0;
                if (codProd) {
                    dadosPorta.adicionais.push({
                        codProd: codProd,
                        qtdProd: qtd // pode ser 0
                    });
                }
            });
            console.log("JSON da porta:", dadosPorta);
            portas.push(dadosPorta);
        });
        console.log("=== JSON FINAL ===");
        console.log(portas);
        $("#id_json_portas").val(JSON.stringify(portas));
        return true;
    }
    $('#openModalBtn').on('click', async function (e) {
        e.preventDefault();
        e.stopPropagation();
        await atualizarSubtotal();
        const temPintura = $("#id_pintura").val();
        const corSelecionada = $("#id_cor").val();
        // Filial
        const filialData = $('#id_vinc_fil').select2('data');
        const filial = filialData[0]?.id;
        // Técnico/Solicitante
        const solicitanteData = $('#id_solicitante').select2('data');
        const solicitante = solicitanteData[0]?.id;
        // Cliente
        const clienteData = $('#id_cli').select2('data');
        const cliente = clienteData[0]?.id;
        if (temPintura === "Sim" && (!corSelecionada || corSelecionada === "")) {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Escolha uma cor da pintura antes de gravar!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
            $("#medidasBtn").click();
            return false;
        }
        if (!filial) {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Filial deve ser informada!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
            $("#clienteBtn").click();
            return false;
        }
        if (!solicitante) {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Solicitante deve ser informado!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
            $("#clienteBtn").click();
            return false;
        }
        if (!cliente) {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Cliente deve ser informado!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
            $("#clienteBtn").click();
            return false;
        }
        if (!verificarTotalFormas()) {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Total das formas de pagamento não corresponde ao valor total!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
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
        aplicarMascaras();
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
    const prodManager = {
        data: {},
        currentEditing: {
            porta: null,
            index: null,
            $tr: null
        },
        setEditingItem($tr) {
            this.currentEditing = {
                porta: Number($tr.data('porta')), // 👈 AQUI
                itemId: Number($tr.data('item-id')),
                $tr: $tr
            };
        },
        updateEditingItem(cells) {
            const { porta, itemId, $tr } = this.currentEditing;
            const portaKey = Number(porta);
            console.log('DATA ATUAL ProdManager:', prodManager.data);
            if (!this.data[portaKey]) {
                console.warn('Porta não existe em this.data', portaKey, this.data);
                return;
            }
            const item = this.data[portaKey].find(i => i.id == itemId);
            if (!item) {
                console.warn('Item não encontrado', porta, itemId, this.data[porta]);
                return;
            }
            // DOM
            $tr.find('td:eq(1)').text(cells[0]);
            $tr.find('td:eq(2)').text(cells[1]);
            $tr.find('td:eq(3)').text(cells[2]);
            $tr.find('td:eq(5)').text(cells[3]);
            $tr.find('td:eq(6)').text(cells[4]);
            // DATA
            item.cod     = cells[0];
            item.desc    = cells[1];
            item.unid    = cells[2];
            item.vl_unit = parseFloat(cells[3]);
            item.qtd     = parseFloat(cells[4]);
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            atualizarJSONPortas();
        },
        clearEditing() {
            this.currentEditing = { porta: null, index: null, $tr: null };
        },
        ensurePorta(porta) {
            if (!this.data[porta]) this.data[porta] = [];
        },
        addItem(porta, item) {
            this.ensurePorta(porta);
            this.data[porta].push(item);
            this.updateHiddenInput();
        },
        removeItem(porta, index) {
            if (!this.data[porta]) return;
            this.data[porta].splice(index, 1);
            this.updateHiddenInput();
        },
        updateItem(porta, index, newData) {
            if (!this.data[porta]) return;
            Object.assign(this.data[porta][index], newData);
            this.updateHiddenInput();
        },
        updateHiddenInput() {
            $("#id_json_portas").val(JSON.stringify(this.data));
        },
        resetPorta(porta) {
            this.data[porta] = [];
            this.updateHiddenInput();
        }
    };
    const prodAdcManager = {
        data: {},
        currentEditing: {
            porta: null,
            index: null,
            $tr: null
        },
        setEditingItem($tr) {
            this.currentEditing = {
                porta: Number($tr.data('porta')), // 👈 AQUI
                itemId: Number($tr.data('item-id')),
                $tr: $tr
            };
        },
        updateEditingItem(cells) {
            const { porta, itemId, $tr } = this.currentEditing;
            const portaKey = Number(porta);
            console.log('DATA ATUAL ProdAdcManager:', prodAdcManager.data);
            if (!this.data[portaKey]) {
                console.warn('Porta não existe em this.data', portaKey, this.data);
                return;
            }
            const item = this.data[portaKey].find(i => i.id == itemId);
            if (!item) {
                console.warn('Item não encontrado', porta, itemId);
                return;
            }
            // 🔹 Atualiza DOM
            $tr.find('td:eq(1)').text(cells[0]);
            $tr.find('td:eq(2)').text(cells[1]);
            $tr.find('td:eq(3)').text(cells[2]);
            $tr.find('td:eq(5)').text(cells[3]);
            $tr.find('td:eq(6)').text(cells[4]);
            // 🔹 Atualiza dados
            item.cod     = cells[0];
            item.desc    = cells[1];
            item.unid    = cells[2];
            item.vl_unit = parseFloat(cells[3]);
            item.qtd     = parseFloat(cells[4]);
            atualizarTabelaPorta(porta);
            atualizarSubtotal();
            atualizarJSONPortas();
        },
        clearEditing() {
            this.currentEditing = { porta: null, index: null, $tr: null };
        },
        ensurePorta(porta) {
            if (!this.data[porta]) this.data[porta] = [];
        },
        addItem(porta, item) {
            this.ensurePorta(porta);
            this.data[porta].push(item);
            this.updateHiddenInput();
        },
        removeItem(porta, index) {
            if (!this.data[porta]) return;
            this.data[porta].splice(index, 1);
            this.updateHiddenInput();
        },
        updateItem(porta, index, newData) {
            if (!this.data[porta]) return;
            Object.assign(this.data[porta][index], newData);
            this.updateHiddenInput();
        },
        updateHiddenInput() {
            $("#id_json_portas").val(JSON.stringify(this.data));
        },
        resetPorta(porta) {
            this.data[porta] = [];
            this.updateHiddenInput();
        }
    };
    function rebuildProdutosFromTable() {
        prodManager.data = {};
        $('.tabela-produtos tbody tr').each(function () {
            const $tr = $(this);
            const porta  = Number($tr.data('porta'));
            const itemId = Number($tr.data('item-id'));
            if (!porta || !itemId) return;
            if (!prodManager.data[porta]) {
                prodManager.data[porta] = [];
            }
            prodManager.data[porta].push({
                id: itemId,
                cod: itemId,
                desc: $tr.find('td:eq(2)').text().trim(),
                unid: $tr.find('td:eq(3)').text().trim(),
                vl_compra: parseFloat($tr.find('td:eq(4)').text().replace(',', '.')) || 0,
                vl_unit: parseFloat($tr.find('td:eq(5)').text().replace(',', '.')) || 0,
                qtd: parseFloat($tr.find('td:eq(6)').text().replace(',', '.')) || 0,
                total: parseFloat($tr.find('td:eq(8)').text().replace(',', '.')) || 0
            });
        });
        prodManager.updateHiddenInput();
    }
    function rebuildAdicionaisFromTable() {
        prodAdcManager.data = {};
        $('.tabela-adicionais tbody tr').each(function () {
            const $tr = $(this);
            const porta  = Number($tr.data('porta'));
            const itemId = Number($tr.data('item-id'));
            if (!porta || !itemId) return;
            if (!prodAdcManager.data[porta]) {
                prodAdcManager.data[porta] = [];
            }
            prodAdcManager.data[porta].push({
                id: itemId,
                cod: itemId,
                desc: $tr.find('td:eq(2)').text().trim(),
                unid: $tr.find('td:eq(3)').text().trim(),
                vl_compra: parseFloat($tr.find('td:eq(4)').text().replace(',', '.')) || 0,
                vl_unit: parseFloat($tr.find('td:eq(5)').text().replace(',', '.')) || 0,
                qtd: parseFloat($tr.find('td:eq(6)').text().replace(',', '.')) || 0,
                total: parseFloat($tr.find('td:eq(8)').text().replace(',', '.')) || 0
            });
        });
        prodAdcManager.updateHiddenInput();
    }
    rebuildProdutosFromTable();
    rebuildAdicionaisFromTable();
    $('.modal').on('hidden.bs.modal', function () {
        $('.modal-backdrop').remove();
        $('body').removeClass('modal-open');
    });
    // Eventos comuns
    $(document).on('click', '.editBtn', function () {
        const $tr = $(this).closest('tr');
        // Identifica tabela
        const isProd = $(this).closest('table').is('#tblProd_' + $tr.data('porta'));
        const isAdc  = $(this).closest('table').is('#tblAdc_' + $tr.data('porta'));
        // ======== PRODUTOS PRINCIPAIS ============
        if (isProd) {
            prodManager.setEditingItem($tr);
            $('#editItemModal .modal-title').html(
                `<i class="fa-solid fa-pen-to-square"></i> Editar Item ${$tr.find('td:eq(0)').text().trim()}`
            );
            $('#editCódInput').val($tr.find('td:eq(1)').text().trim());
            $('#editDescInput').val($tr.find('td:eq(2)').text().trim());
            $('#editUnidInput').val($tr.find('td:eq(3)').text().trim());
            $('#editValorItemInput').val($tr.find('td:eq(5)').text().trim());
            $('#editQtdInput').val($tr.find('td:eq(6)').text().trim());
            const modalEdit = new bootstrap.Modal(document.getElementById('editItemModal'));
            modalEdit.show();
        }
        // ======== PRODUTOS ADICIONAIS ============
        else if (isAdc) {
            prodAdcManager.setEditingItem($tr);
            $('#editItemAdcModal .modal-title').html(
                `<i class="fa-solid fa-pen-to-square"></i> Editar Item ${$tr.find('td:eq(1)').text().trim()}`
            );
            $('#editCódAdcInput').val($tr.find('td:eq(1)').text().trim());
            $('#editDescAdcInput').val($tr.find('td:eq(2)').text().trim());
            $('#editUnidAdcInput').val($tr.find('td:eq(3)').text().trim());
            $('#editValorItemAdcInput').val($tr.find('td:eq(5)').text().trim());
            $('#editQtdAdcInput').val($tr.find('td:eq(6)').text().trim());
            const modalAdc = new bootstrap.Modal(document.getElementById('editItemAdcModal'));
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
    function addForma(formaPgto, valor) {
        const valorNumero = parseFloat(valor) || 0;
        const valorExibicao = valorNumero.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
        // 👉 Exibe na tabela
        formaManager.addItem([
            formaPgto,
            valorExibicao
        ]);
        // 👉 Guarda valor REAL no <tr>
        const $ultimaLinha = $('#itensTableForm tbody tr:last');
        $ultimaLinha.data('valor', valorNumero);
        // Atualizações
        atualizarSubtotal();
        verificarTotalFormas();
        calcularValorForma();   // ← recalcula o restante
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
    $('#addItemValorFormBtn').on('click', function (e) {
        e.preventDefault();
        e.stopImmediatePropagation();
        const selectData = $('#id_formas_pgto').select2('data');
        const formaPgto = selectData[0]?.id;
        const valorStr  = $('#id_vl_form_pgto').val();
        const valor     = parseValor(valorStr);
        if (!formaPgto) {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Forma de Pagamento deve ser informada!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
            $("#form_pgtoBtn").click();
            return;
        }
        if (valor <= 0) {
            Toastify({
                text: '<i class="fa-solid fa-triangle-exclamation"></i> Informe um valor válido!',
                duration: 5000,
                gravity: "top",
                position: "center",
                stopOnFocus: true,
                escapeMarkup: false,
                backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
            }).showToast();
            return;
        }
        $.ajax({
            url: "/formas_pgto/get/",
            method: "GET",
            data: { id: formaPgto },
            success: function (response) {
                addForma(response.descricao, valor);
                // limpa select e input
                $('#id_formas_pgto').val(null).trigger('change');
                $('#id_vl_form_pgto').val('');
                calcularValorForma();
                // ✅ AGORA SIM: a linha já existe
                gerarJSONFormas();
            },
            error: function () {
                Toastify({
                    text: '<i class="fa-solid fa-triangle-exclamation"></i> Erro ao buscar a Forma de Pagamento!',
                    duration: 5000,
                    gravity: "top",
                    position: "center",
                    stopOnFocus: true,
                    escapeMarkup: false,
                    backgroundColor: "linear-gradient(to right, #d58300, #ffc93b)",
                }).showToast();
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
    $(document).ready(function () {
        $(document).on("blur", ".larg, .alt", function () {
            let porta = $(this).data("porta"); 
            const larg = $(`.larg[data-porta="${porta}"]`).val().trim();
            const alt  = $(`.alt[data-porta="${porta}"]`).val().trim();
            if (!larg || !alt) return;
            const lg = parseFloat(larg.replace(",", "."));
            const at = parseFloat(alt.replace(",", "."));
            if (lg === lastLg && at === lastAt) {
                console.log("Largura/altura não mudaram — não recalculando.");
                return;
            }
            lastLg = lg;
            lastAt = at;
            atualizarSubtotal();
        });
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
            const temPintura = $("#id_pintura").val();
            if (temPintura === "Não") {
                $(`#tblAdc_${porta} tbody tr`).each(function () {
                    const desc = $(this).find("td:nth-child(3)").text().toUpperCase().trim();
                    if (desc === "PINTURA ELETROSTÁTICA" || desc === "PINTURA AUTOMOTIVA") {
                        $(this).remove();
                    }
                });
                calcularValorForma();
                atualizarTabelaPorta(porta);
                atualizarSubtotal();
                somaFormas();
                return;
            }
            prodAdcManager.updateHiddenInput();
        });
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
                        Toastify({
                            text: 'Código de produto não encontrado!',
                            duration: 5000,
                            gravity: "top",
                            position: "center",
                            backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                            stopOnFocus: true,
                            escapeMarkup: false,
                        }).showToast();
                    }
                },
                error: function() {
                    Toastify({
                        text: 'Erro ao buscar o produto. Tente novamente!',
                        duration: 5000,
                        gravity: "top",
                        position: "center",
                        backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                        stopOnFocus: true,
                        escapeMarkup: false,
                    }).showToast();
                }
            });
        }
    });
    $('#id_cod_produto').on('blur keydown', function(event) {
        if (event.type === 'blur' || event.key === 'Enter') {
            const productId = $(this).val();
            const tpProduto = $('#id_tp_produto').val(); // Obtém o valor do select
            if (productId.trim() === '') {
                return; // Sai da função se o campo estiver vazio
            }
            $.ajax({
                url: '/produtos/lista_ajax_ent/', // Substitua pela URL correta da sua aplicação
                method: 'GET',
                data: {
                    s: productId,
                    tp: 'cod',
                    tp_prod: '' // Inclui o tipo de produto na requisição
                },
                success: function(response) {
                    if (response.produtos.length > 0) {
                        const produto = response.produtos[0];
                        $('#id_desc_prod').val(produto.desc_prod);
                        $('#id_unidProduto').val(produto.unidProd);
                        $('#id_grupoProd').val(produto.grupo);
                        $('#id_preco_unit').focus();
                    } else {
                        Toastify({
                            text: 'Código de produto não encontrado!',
                            duration: 5000,
                            gravity: "top",
                            position: "center",
                            backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                            stopOnFocus: true,
                            escapeMarkup: false,
                        }).showToast();
                        $('#id_cod_produto').focus();
                    }
                },
                error: function() {
                    Toastify({
                        text: 'Erro ao buscar o produto. Tente novamente!',
                        duration: 5000,
                        gravity: "top",
                        position: "center",
                        backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                        stopOnFocus: true,
                        escapeMarkup: false,
                    }).showToast();
                }
            });
        }
    });
    $('#id_cod_prod_adc').on('blur keydown', function(event) {
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
                    tp_prod: 'Adicional' // Inclui o tipo de produto na requisição
                },
                success: function(response) {
                    if (response.produtos.length > 0) {
                        const produto = response.produtos[0];
                        $('#id_desc_prod_adc').val(produto.desc_prod);
                        $('#id_unidProd_adc').val(produto.unidProd);
                        $('#id_vl_compra_adc').val(produto.vl_compra);
                        $('#id_vl_prod_adc').val(produto.vl_prod);
                        if (produto.vl_prod === "0,00" || produto.vl_prod === "") {
                            $('#id_vl_prod_adc').focus();
                        } else {
                            $('#id_qtd_prod_adc').focus();
                        }
                        const descricao = $('#id_desc_prod_adc').val();
                        const tp_pintura = $("#id_tp_pintura").val();
                        console.log('Cálculo do produto', descricao)
                        if ((tp_pintura === "Eletrostática" && descricao === 'PINTURA ELETROSTÁTICA') || (tp_pintura === "Automotiva" && descricao === "PINTURA AUTOMOTIVA")) {
                            console.log('Valor de id_m2 antes da leitura:', $('#id_m2').val().replace(',', '.'));
                            let m2 = parseFloat($('#id_m2').val().replace(',', '.'));
                            if (!isNaN(m2)) {
                                $('#id_qtd_prod_adc').val(m2.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
                            } else {
                                $('#id_qtd_prod_adc').val('0,00');
                            }
                            const temPintura = $('#id_pintura').val();
                            let toastErrorShown = false;
                            if (temPintura === 'Sim') {
                                $('#id_qtd_prod_adc').val('1,00');
                            } else {
                                if (!toastErrorShown) { // Só exibe a mensagem se ainda não foi mostrada
                                    toastErrorShown = true;
                                    Toastify({
                                        text: '<i class="fa-solid fa-triangle-exclamation"></i> Campo Pintura está selecionado como Não, para inserir o produto, altere a opção para Sim!',
                                        duration: 5000,
                                        gravity: "top",
                                        position: "center",
                                        backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                                        stopOnFocus: true,
                                        escapeMarkup: false,
                                    }).showToast();
                                    setTimeout(() => {
                                        finalizarLoading();
                                    }, 500);
                                    $('#id_cod_prod_adc').focus();
                                }
                                return;
                            }
                            atualizarSubtotal();
                            toastErrorShown = false;
                        }
                    } else {
                        Toastify({
                            text: 'Código de produto não encontrado!',
                            duration: 5000,
                            gravity: "top",
                            position: "center",
                            backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                            stopOnFocus: true,
                            escapeMarkup: false,
                        }).showToast();
                    }
                },
                error: function() {
                    Toastify({
                        text: 'Erro ao buscar o produto. Tente novamente!',
                        duration: 5000,
                        gravity: "top",
                        position: "center",
                        backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)',
                        stopOnFocus: true,
                        escapeMarkup: false,
                    }).showToast();
                }
            });
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
                Toastify({
                    text: "Link copiado!",
                    duration: 5000,
                    gravity: "top", // Posição da notificação
                    position: "center", // Centralizado no topo
                    backgroundColor: "linear-gradient(to right, #00b09b, #96c93d)", // Verde sucesso
                    stopOnFocus: true,
                }).showToast();
            }).catch(err => console.error("Erro ao copiar: ", err));
        } else {
            // Fallback para navegadores antigos
            let tempInput = $("<input>");
            $("body").append(tempInput);
            tempInput.val(link).select();
            document.execCommand("copy");
            tempInput.remove();
            Toastify({
                text: "Link copiado!",
                duration: 5000,
                gravity: "top",
                position: "center",
                backgroundColor: "linear-gradient(to right, #00b09b, #96c93d)",
                stopOnFocus: true,
            }).showToast();
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
        activeBt.addClass('btn-ativo').removeClass('btn-inativo');
        bt1.removeClass('btn-ativo btn-inativo');
        bt2.removeClass('btn-ativo btn-inativo');
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
    let selectors = '#campo_1, #campo_2, #id_margem, #id_vl_prod, .inpFrete, #id_quantidade, #total-frete, .editable, #id_preco_unit, #id_valor_mensalidade, #id_vl_mens, #id_qtd, #id_m2, #id_acrescimo, #id_desconto, #id_vl_compra, #id_vl_compra_adc, #id_estoque_prod, #campo_desconto, #campo_acrescimo';
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