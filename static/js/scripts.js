$(document).ready(function() {
    var form = $('#createForm');
    var cadastro = 'https://allitec.pythonanywhere.com/orcamentos/add/';
    calcTotalEntrada();
    $('.table').addClass("table-sm");
    $('[name^="nome_"]').first().focus();
    $('[name^="descricao"]').first().focus();
    // Novo teste
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

        // Se o select estiver DESABILITADO → habilita
        if ($select.prop("disabled")) {
            $select.prop("disabled", false);
            $cancel.show();
            return; // primeira etapa concluída
        }

        // Se o select já estiver habilitado → abrir modal
        const novoStatus = $select.find("option:selected").text();

        // Inserir texto dentro do modal correspondente
        $(`#novoStatusTexto${id}`).text(novoStatus);

        // Abrir modal correto
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
                $("#data-btn").click();
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

        // Se tiver marcado, abre o modal normalmente
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
        // Preenche a "Dt 1ª Parcela" inicialmente
        if (dtEfetivacao.val()) {
            inpDtPriParc.val(addDtInterv(dtEfetivacao.val(), inpDiasPriParc.val()));
        }
        // Atualiza sempre que mudar a data ou os dias da 1ª parcela
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
    // $('#id_desconto, #id_estoque_prod').on("blur", function() {
    //     let valor = $(this).val().replace(',', '.').trim();
    //     if (valor === "" || isNaN(valor)) {
    //         $(this).val("0.00");
    //     } else {
    //         $(this).val(parseFloat(valor).toFixed(2));
    //     }
    // });
    $(document).on("click", ".editable#total-frete", function () {
        const $span = $(this);
        const valor = $span.text().trim();
        const $input = $(`<input type="text" id="total-frete" class="form-control d-inline-block w-auto inpFrete" value="${valor}">`);
        $span.replaceWith($input);
        $input.focus().select();
        // máscara no input enquanto digita
        $input.on("input", function() {
            let val = $(this).val().replace(/[^0-9]/g, ""); // mantém só números
            if (val === "") {
                $(this).val("0.00");
                return;
            }
            // transforma em número decimal
            let num = (parseFloat(val) / 100).toFixed(2);
            // formata com ponto decimal
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
                // substitui pelo span formatado
                const $newSpan = $(`
                    <span class="editable" id="total-frete"
                          style="background-color: #F08080; color: white; border-radius: 15px; padding-left: 10px; padding-right: 10px; float: right;">
                        ${novoValorNum.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                `);
                $input.replaceWith($newSpan);
                // atualiza o hidden
                $('#id_frete').val(novoValorNum.toFixed(2));
                // recalcula totais
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
            // Verifica se já existe um <input hidden> com esse código dentro da tabela
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


    //
    // Pra Adicionar Tabela de Preço de Produto
    //
    let trEdit = null;          // variável global para edição
    let identificador = $("#tab-prec tbody tr").length; // contador inicial
    let editing = false;        // flag para evitar sobrescrever margem ao editar
    let bloqueio = false;       // evita loop de eventos

    // ======= REACALCULOS AUTOMÁTICOS =======
    // Recalcular MARGEM ao editar VALOR PRODUTO
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

        // Validações
        if (!tabId) {
            Toastify({ text: 'Selecione uma tabela antes de adicionar!', duration: 5000, gravity: "top", position: "center", backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)', stopOnFocus: true }).showToast();
            return;
        }
        if (vl_p === "0.00" || vl_p === "" || vl_p === "0") {
            Toastify({ text: 'Preço de Venda deve ser informado!', duration: 5000, gravity: "top", position: "center", backgroundColor: 'linear-gradient(to right, #d58300, #ffc93b)', stopOnFocus: true }).showToast();
            return;
        }

        if (trEdit) {
            // === Atualizar linha existente ===
            let idx = trEdit.data("id");
            trEdit.find("td:eq(0)").html(`${tabNome}<input type="hidden" name="tab_preco[${idx}][tabela]" value="${tabId}">`);
            trEdit.find("td:eq(1)").html(`${mrg}<input type="hidden" name="tab_preco[${idx}][margem]" value="${mrg}">`);
            trEdit.find("td:eq(2)").html(`${vl_p}<input type="hidden" name="tab_preco[${idx}][vl_prod]" value="${vl_p}">`);
            trEdit = null;
            $("#id_tabela").prop("disabled", false);
            // Volta o botão para "Incluir"
            $('#add-tab')
                .css('background-color', '')
                .html('<i class="fa-solid fa-plus"></i> Incluir');
        } else {
            // === Criar nova linha ===
            let idx = identificador++;
            $("#tab-prec tbody tr.vazio").remove();

            // Verifica duplicidade
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
    // const descricao = $(this).data('description') || '';
    // const solicitacaoId1 = $(this).data('id');
    // if (!solicitacaoId1) {
    //     console.error('ID da solicitação não encontrado!');
    //     alert('Erro: ID da solicitação não encontrado.');
    //     return;
    // }
    // console.log('Descrição:', descricao);
    // console.log('ID capturado:', solicitacaoId1);
    // $('#descricaoSolicitacao').text(descricao);
    // $('#solicitacaoId').val(solicitacaoId1);
    // $('#modalSolicitacao').modal('show');
    //
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
    // Função auxiliar para adicionar produto em qualquer TableManager
    function adicionarProduto(manager, produto, qtd) {
        const valorCompraTotal = (parseFloat(produto.vl_compra) * qtd).toFixed(2);
        const valorTotal = (parseFloat(produto.vl_prod) * qtd).toFixed(2);
        manager.addItem([
            produto.id,
            produto.desc_prod,
            produto.unidProd,
            produto.vl_compra,
            produto.vl_prod,
            qtd,
            valorCompraTotal,
            valorTotal
        ]);
        atualizarSubtotal(); // Atualiza o subtotal após adicionar o produto
    }

    // Função auxiliar: verifica se o produto já está na tabela
    function produtoJaExiste(produtoId) {
        let existe = false;
        $('#itensTableProduto tbody tr').each(function () {
            let idTabela = $(this).find('td:nth-child(2)').text().trim(); // Ajuste para a coluna do ID
            if (idTabela == produtoId) {
                existe = true;
                return false; // interrompe loop
            }
        });
        return existe;
    }
    function produtoAdcJaExiste(produtoId) {
        let existe = false;
        $('#itensTableProdutoAdc tbody tr').each(function () {
            let idTabela = $(this).find('td:nth-child(2)').text().trim(); // Ajuste para a coluna do ID
            if (idTabela == produtoId) {
                existe = true;
                return false; // interrompe loop
            }
        });
        return existe;
    }

    function buscarProdutosPrincipais() {
        $.ajax({
            url: '/produtos/lista_ajax/',
            method: 'GET',
            data: { tp: 'desc', tp_prod: 'Principal' },
            success: function(response) {
                console.log('%cProdutos Principais retornados:', 'color:yellow;', response.produtos);
                if (!response.produtos || response.produtos.length === 0) {
                    console.warn('Nenhum produto principal encontrado!');
                    return;
                }
                const lg = parseFloat($('#id_larg').val().replace(',', '.')) || 0;
                const at = parseFloat($('#id_alt').val().replace(',', '.')) || 0;
                const tpLamina = $('#id_tp_lamina').val(); // valor do select
                const produtosOrdenados = response.produtos.sort((a, b) => a.id - b.id);
                produtosOrdenados.forEach(produto => {
                    if (produto.desc_prod.toLowerCase().startsWith('motor')) {
                        console.log("Ignorando MOTOR — motor só será inserido pelo cálculo.");
                        return;
                    }
                    if (tpLamina === 'Fechada' && produto.desc_prod === 'LÂMINAS TRANSVISION') {
                        console.log('Ignorado LÂMINAS TRANSVISION porque tp_lamina = Fechada');
                        return;
                    }
                    if (tpLamina === 'Transvision' && produto.desc_prod === 'LÂMINAS LISAS') {
                        console.log('Ignorado LÂMINA LISA porque tp_lamina = Transvision');
                        return;
                    }
                    if ((lg > 0 || at > 0) && !produtoJaExiste(produto.id)) {
                        adicionarProduto(prodManager, produto, 1);
                    } else if (produtoJaExiste(produto.id)) {
                        console.log(`Produto já existe: ${produto.desc_prod}`);
                    }
                });
                setTimeout(() => {
                    $('#itensTableProduto tbody tr').each(function () {
                        let descricao = $(this).find('td:nth-child(3)').text().trim();
                        if (tpLamina === 'Fechada' && descricao === 'LÂMINAS TRANSVISION') {
                            console.log('Removendo LÂMINA TRANSVISION porque tp_lamina = Fechada');
                            $(this).remove();
                        }
                        if (tpLamina === 'Transvision' && descricao === 'LÂMINAS LISAS') {
                            console.log('Removendo LÂMINA LISA porque tp_lamina = Transvision');
                            $(this).remove();
                        }
                    });
                    // removerProdutoMotor();
                    // buscarMotorIdeal();
                    calcularValorForma();
                    somaFormas();
                    // validarProdutos();
                    atualizarTabela();
                    atualizarSubtotal(); // Certifique-se de que o subtotal é atualizado aqui também
                }, 100);
            },
            error: function() {
                Toastify({
                    text: 'Erro ao buscar produtos principais!',
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
    // Buscar produtos adicionais
    // Função para normalizar strings (remove acentos e espaços extras)
    function normalizarTexto(txt) {
        return txt
            .normalize("NFD")               // separa acentos
            .replace(/[\u0300-\u036f]/g, "") // remove acentos
            .toUpperCase()
            .trim();
    }
    function buscarProdutosAdicionais() {
        $.ajax({
            url: '/produtos/lista_ajax/',
            method: 'GET',
            data: { tp: 'desc', tp_prod: 'Adicional' },
            success: function(response) {
                if (!response.produtos || response.produtos.length === 0) return;
                const lg = parseFloat($('#id_larg').val().replace(',', '.')) || 0;
                const at = parseFloat($('#id_alt').val().replace(',', '.')) || 0;
                const tp_pintura = $('#id_tp_pintura').val();
                const produtosOrdenados = response.produtos.sort((a, b) => a.id - b.id);
                produtosOrdenados.forEach(produto => {
                    if (tp_pintura === 'Eletrostática' && produto.desc_prod === 'PINTURA AUTOMOTIVA') return;
                    if (tp_pintura === 'Automotiva' && produto.desc_prod === 'PINTURA ELETROSTÁTICA') return;
                    if ((lg > 0 || at > 0) && !produtoAdcJaExiste(produto.id)) {
                        adicionarProduto(prodAdcManager, produto, 0);
                    } else if (produtoAdcJaExiste(produto.id)) {
                        console.log(`Produto Adicional já existe: ${produto.desc_prod}`);
                    }
                });
                setTimeout(() => {
                    $('#itensTableProdutoAdc tbody tr').each(function () {
                        let descricao = $(this).find('td:nth-child(3)').text().trim();
                        if (tp_pintura === 'Eletrostática' && descricao === 'PINTURA AUTOMOTIVA') {
                            $(this).remove();
                        }
                        if (tp_pintura === 'Automotiva' && descricao === 'PINTURA ELETROSTÁTICA') {
                            $(this).remove();
                        }
                    });
                    calcularValorForma();
                    somaFormas();
                    atualizarTabela();
                    atualizarSubtotal();
                }, 80);
                verificarPintura();           // remove as pinturas erradas
                prodAdcManager.updateHiddenInput();
            }
        });
    }
    // Chama a função para buscar produtos ao carregar a página
    // Função para limpar a tabela e reiniciar contador
    function resetTable(tableId, managerInstance) {
        $("#" + tableId).find("tbody").empty();
        if (managerInstance) {
            managerInstance.itemCount = 1; // reinicia contador de linhas
        }
        return 0; // retorna o contador zerado
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
    function calcFtPeso() {
        let alt_corte = parseFloat($('#id_alt_corte').val().replace(',', '.'));
        let tp_vao = $('#id_tp_vao').val();
        if (isNaN(alt_corte)) {
            $('#id_fator_peso').val('');
            return;
        }
        let resultado;
        if (tp_vao === "Fora do Vão") {
            resultado = (alt_corte + 0.6) / 7.5;
        } else {
            resultado = (alt_corte - 0.6) / 7.5;
        }
        let final = arredondarParaCima(resultado, 2) * 100;
        $('#id_fator_peso').val(final.toFixed(2));
    }
    $('#id_alt').on('keyup change', function () {
        $('#id_alt_corte').val($(this).val());
    });
    $('#id_tp_vao').val('Fora do Vão');
    function finalizarLoading() {
        setTimeout(() => {
            $("#loadingModal").modal("hide");
        }, 1500);
    }
    function calcLgCorte() {
        let largRaw = $("#id_larg").val();
        if (!largRaw) return "";
        let larg = parseFloat(largRaw.replace(/,/g, ""));
        if (isNaN(larg)) return "";
        const tpLam = $("#id_tp_vao").val();
        let calc = 0;
        if (tpLam === "Fora do Vão") {
            calc = larg + 0.10;
        } else {
            calc = larg - 0.08;
        }
        if (tpLam === '1 Lado Dentro do Vão') {
            calc = larg + 0.03;
        }
        return calc.toFixed(2);
    }
    function atualizarLarguraCorte() {
        const result = calcLgCorte();
        $('#id_larg_corte').val(result);

        let ft_p = $('#id_fator_peso').val();
        ft_p = ft_p ? parseFloat(ft_p.replace(',', '.')) : 0;

        const calculo = (result * 0.8) * ft_p * 1.2;
        const pesoFinal = arredondarParaCima(calculo, 0);

        console.log("calcLgCorte():", result);
        console.log("fator peso (ft_p):", ft_p);
        console.log("cálculo bruto:", calculo);
        console.log("peso final:", pesoFinal);
        $("#id_peso").val(pesoFinal);
    }
    function calcularEixoMotor() {
        let ft_peso = parseFloat($('#id_fator_peso').val());
        let larg_corte = parseFloat($('#id_larg_corte').val());
        let qtd = 1;
        if (isNaN(ft_peso) || isNaN(larg_corte) || isNaN(qtd)) {
            $('#id_eixo_motor').val('');
            return;
        }
        let calc = (((larg_corte * 0.8) * ft_peso) * (1.5 * qtd));
        let final = arredondarParaCima(calc, 0);
        $('#id_eixo_motor').val(final);
    }
    function calcM2() {
        let larg_corte = parseFloat($('#id_larg_corte').val());
        let alt_corte = parseFloat($('#id_alt_corte').val());
        let rolo = parseFloat($('#id_rolo').val());
        let qtd = parseFloat($('#id_qtd').val());
        let calc = ((rolo + alt_corte) * larg_corte) * qtd;
        let aux = arredondarComAjuste(calc);
        $('#id_m2').val(aux);
    }
    function calcQtdLam() {
        let alt_corte = parseFloat($('#id_alt_corte').val());
        let rolo = parseFloat($('#id_rolo').val());
        let calc = (alt_corte + rolo) / 0.075;
        let aux = arredondarInteiro(calc);
        $('#id_qtd_lam').val(aux);
    }
    let ultimoMotorGerado = null;
    let ultimoPesoUsado = null;
    let motorJaInserido = false;
    function buscarMotorIdeal() {
        const peso = parseFloat($('#id_peso').val()) || 0;
        if (peso < 1) return;
        const ranges = [150,250,350,450,550,650,750,1000];
        const modelos = ["200KG","300KG","400KG","500KG","600KG","700KG","800KG","1000KG"];
        const motor = `MOTOR ${modelos[ranges.findIndex(r => peso <= r)] || "1500KG"}`;
        if (motorJaInserido && peso === ultimoPesoUsado && motor === ultimoMotorGerado) {
            return;
        }
        removerProdutoMotor();
        $.get('/produtos/lista_ajax/', { s: motor, filtro: 'desc', tp_prod: 'Principal' })
            .done(res => {
                const p = res.produtos?.[0];
                if (!p || verificarProduto(p.desc_prod)) return;
                setTimeout(() => {
                    adicionarProduto(prodManager, p, "1.00");
                    calcularEixoMotor();
                    ultimoPesoUsado = peso;
                    ultimoMotorGerado = motor;
                    motorJaInserido = true;
                }, 1500); // 1000ms = 1 segundo
            })
            .fail(() => {
                Toastify({
                    text: 'Erro ao buscar motor ideal.',
                    duration: 5000, gravity:"top", position:"center",
                    backgroundColor:'linear-gradient(to right, #db1e47, #ff7373)'
                }).showToast();
            });
    }
    function removerProdutoMotor() {
        $('#itensTableProduto tbody tr').filter((_, tr) =>
            $(tr).find('td:nth-child(3)').text().toLowerCase().startsWith('motor')
        ).remove();
    }
    function verificarProduto(nome) {
        const n = nome.toLowerCase();
        return $('#itensTableProduto tbody tr').filter((_, tr) =>
            $(tr).find('td:nth-child(3)').text().toLowerCase() === n
        ).length > 0;
    }
    function verificarPintura() {
        const temPintura = $("#id_pintura").val();
        const tp_pintura = $("#id_tp_pintura").val();
        const prodCerto =
            tp_pintura === "Eletrostática"
                ? "PINTURA ELETROSTÁTICA"
                : "PINTURA AUTOMOTIVA";
        const prodErrado =
            tp_pintura === "Eletrostática"
                ? "PINTURA AUTOMOTIVA"
                : "PINTURA ELETROSTÁTICA";
        if (temPintura === "Não") {
            $('#itensTableProdutoAdc tbody tr').each(function () {
                const desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
                if (desc.includes("PINTURA")) {
                    $(this).remove();
                }
            });
            atualizarSubtotal();
            calcularValorForma();
            somaFormas();
            atualizarTabela();
            setTimeout(() => {
                finalizarLoading();
            }, 500);
            return;
        }
        $('#itensTableProdutoAdc tbody tr').each(function () {
            const desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
            if (desc === prodErrado.toUpperCase()) {
                $(this).remove();
            }
        });
        let existe = false;
        $('#itensTableProdutoAdc tbody tr').each(function () {
            const desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
            if (desc === prodCerto.toUpperCase()) {
                existe = true;
            }
        });
        if (existe) {
            atualizarSubtotal();
            calcularValorForma();
            somaFormas();
            atualizarTabela();
            setTimeout(() => {
                finalizarLoading();
            }, 500);
            return;
        }
        if (tp_pintura === "Eletrostática" && prodCerto !== "PINTURA ELETROSTÁTICA") {
            setTimeout(() => {
                finalizarLoading();
            }, 500);
            return;
        }
        if (tp_pintura === "Automotiva" && prodCerto !== "PINTURA AUTOMOTIVA") {
            setTimeout(() => {
                finalizarLoading();
            }, 500);
            return;
        }
        $.ajax({
            url: '/produtos/lista_ajax/',
            method: 'GET',
            data: { tp: 'desc', filtro: 'PINTURA' },
            success: function (response) {
                if (!response.produtos || !response.produtos.length) {
                    setTimeout(() => {
                        finalizarLoading();
                    }, 500);
                    return;
                }
                let jaExiste = false;
                $('#itensTableProdutoAdc tbody tr').each(function () {
                    const desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
                    if (desc === prodCerto.toUpperCase()) {
                        jaExiste = true;
                    }
                });
                if (jaExiste) {
                    setTimeout(() => {
                        finalizarLoading();
                    }, 500);
                    return;
                }
                let pinturaProd = response.produtos.find(
                    p => p.desc_prod.toUpperCase().trim() === prodCerto.toUpperCase()
                );
                if (!pinturaProd) {
                    setTimeout(() => {
                        finalizarLoading();
                    }, 500);
                    return;
                }
                setTimeout(() => {
                    adicionarProduto(prodAdcManager, pinturaProd, "1.00");
                    atualizarSubtotal();
                    calcularValorForma();
                    somaFormas();
                    atualizarTabela();
                    setTimeout(() => {
                        finalizarLoading();
                    }, 500);
                }, 200);
            },
            error: function () {
                setTimeout(() => {
                    finalizarLoading();
                }, 500);
            }
        });
    }
    $('#id_larg').on('keyup change', atualizarLarguraCorte);
    $('#id_tp_vao').on('change', atualizarLarguraCorte);

   $('#id_alt').on('blur', function () {
        $("#loadingModal").modal("show");
        calcFtPeso();
        atualizarLarguraCorte();
        calcularEixoMotor();
        calcM2();
        calcQtdLam();
        buscarMotorIdeal();
        verificarPintura();
        setTimeout(() => {
            finalizarLoading();
        }, 500);
    });
    $("#adicionaisBtn").on("click", function () {
        const temPintura = $("#id_pintura").val();
        if (temPintura === "Não") {
            $('#itensTableProdutoAdc tbody tr').each(function () {
                const desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
                if (desc === "PINTURA ELETROSTÁTICA" || desc === "PINTURA AUTOMOTIVA") {
                    $(this).remove();
                }
            });
            atualizarSubtotal();
            calcularValorForma();
            atualizarTabela();
            somaFormas();
            return; // impede que o resto da lógica de pinturas rode
        }
        prodAdcManager.updateHiddenInput();
    });

    $("#id_tp_pintura, #id_pintura").change(function () {
        $("#loadingModal").modal("show");
        verificarPintura();
    });


    // function validarProdutos() {

    //     const tpLam = $('#id_tp_lamina').val();
    //     const tp_pintura = $("#id_tp_pintura").val();

    //     // Verifique se está editando um orçamento existente
    //     const isEditing = $('#id_num_orcamento').val() !== ''; // Ajuste conforme necessário

    //     // --- PINTURA ---
    //     if (temPintura === 'Não') {
    //         // Remove qualquer tipo de pintura
    //         $('#itensTableProdutoAdc tbody tr').each(function () {
    //             let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
    //             if (desc === 'PINTURA ELETROSTÁTICA' || desc === "PINTURA AUTOMOTIVA") {
    //                 $(this).remove();
    //             }
    //         });
    //         $('#itensTableProduto tbody tr').each(function () {
    //             let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
    //             if (desc === 'PINTURA ELETROSTÁTICA' || desc === "PINTURA AUTOMOTIVA") {
    //                 $(this).remove();
    //             }
    //         });
    //         atualizarSubtotal();
    //         return; // não precisa continuar
    //     }

    //     // Se tem pintura, controla o tipo
    //     if (temPintura === 'Sim') {
    //         // --- Remove o tipo de pintura oposto ---
    //         if (tp_pintura === 'Eletrostática') {
    //             removerProdutoPorDescricao('PINTURA AUTOMOTIVA');
    //         } else if (tp_pintura === 'Automotiva') {
    //             removerProdutoPorDescricao('PINTURA ELETROSTÁTICA');
    //         }

    //         if (!isEditing && !carregandoPagina) {
    //             // Verifica se já existe pintura (de qualquer tipo)
    //             let existePintura = false;
    //             $('#itensTableProdutoAdc tbody tr').each(function () {
    //                 let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
    //                 if (desc === 'PINTURA ELETROSTÁTICA' || desc === 'PINTURA AUTOMOTIVA') {
    //                     existePintura = true;
    //                     return false;
    //                 }
    //             });

    //             // Só busca no servidor se realmente não existe
    //             if (!existePintura) {
    //                 $.ajax({
    //                     url: '/produtos/lista_ajax/',
    //                     method: 'GET',
    //                     data: { tp: 'desc', filtro: 'PINTURA' },
    //                     success: function(response) {
    //                         if (response.produtos && response.produtos.length > 0) {
    //                             let pinturaProd = null;

    //                             if (tp_pintura === "Eletrostática") {
    //                                 pinturaProd = response.produtos.find(
    //                                     p => p.desc_prod.toUpperCase().trim() === 'PINTURA ELETROSTÁTICA'
    //                                 );
    //                             } else if (tp_pintura === "Automotiva") {
    //                                 pinturaProd = response.produtos.find(
    //                                     p => p.desc_prod.toUpperCase().trim() === 'PINTURA AUTOMOTIVA'
    //                                 );
    //                             }

    //                             // Verifica se o produto já existe em alguma tabela
    //                             function produtoJaExiste(descProduto) {
    //                                 let existe = false;
    //                                 $('#itensTableProduto tbody tr, #itensTableProdutoAdc tbody tr').each(function () {
    //                                     let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
    //                                     if (desc === descProduto) {
    //                                         existe = true;
    //                                         return false;
    //                                     }
    //                                 });
    //                                 return existe;
    //                             }

    //                             if (
    //                                 adicionaisLiberado &&
    //                                 pinturaProd &&
    //                                 !produtoJaExiste('PINTURA ELETROSTÁTICA') &&
    //                                 !produtoJaExiste('PINTURA AUTOMOTIVA')
    //                             ) {
    //                                 console.log("PINTURA Adicionada");
    //                                 setTimeout(() => {
    //                                     adicionarProduto(prodAdcManager, pinturaProd, 1);
    //                                     atualizarSubtotal();
    //                                     calcularValorForma();
    //                                     atualizarTabela();
    //                                 }, 100);
    //                             } else {
    //                                 console.log("PINTURA ELETROSTÁTICA/AUTOMOTIVA já existe em alguma tabela, não foi adicionada.");
    //                             }
    //                         }
    //                     }
    //                 });
    //             }
    //         }
    //         atualizarSubtotal();
    //     }
    //     carregandoPagina = false;

    //     // --- Função auxiliar para remoção ---
    //     function removerProdutoPorDescricao(descProduto) {
    //         descProduto = descProduto.toUpperCase();
    //         $('#itensTableProduto tbody tr, #itensTableProdutoAdc tbody tr').each(function () {
    //             let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
    //             if (desc === descProduto) {
    //                 $(this).remove();
    //             }
    //         });
    //     }
    //     // --- LÂMINAS ---
    //     if (tpLam === "Fechada") {
    //         $('#itensTableProduto tbody tr').each(function () {
    //             let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
    //             if (desc === 'LÂMINAS TRANSVISION') {
    //                 $(this).remove();
    //             }
    //         });
    //     } else if (tpLam === "Transvision") {
    //         $('#itensTableProduto tbody tr').each(function () {
    //             let desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
    //             if (desc === 'LÂMINAS LISAS') {
    //                 $(this).remove();
    //             }
    //         });
    //     }
    // }


    // function calcularValor() {
    //     let tp_vao = $('#id_tp_vao').val();
    //     let valorE = parseFloat($('#id_larg').val().replace(',', '.'));
    //     if (isNaN(valorE)) {
    //         $('#id_larg_corte').val('');
    //         return;
    //     // Converte valorE para centésimos inteiro, soma ajuste e volta para número com 2 decimais
    //     let valorCentimos = Math.round(valorE * 100);          // ex: 2.88 -> 288
    //     let resultadoCentimos = valorCentimos + ajusteCentimos; // ex: 288 + 10 -> 298
    //     let resultado = resultadoCentimos / 100;               // -> 2.98

    //     if ($('#id_alt').val().trim() !== "") {
    //         $('#id_larg_corte').val(resultado.toFixed(2));
    //     }

    //     let ft_peso = parseFloat($('#id_fator_peso').val());
    //     if (isNaN(ft_peso)) {
    //         ft_peso = "0.00"; // ou return se preferir não calcular peso
    //     }
    //     let calc = (((resultado * 0.8) * ft_peso) * 1.2);
    //     let final = arredondarParaCima(calc, 0);
    //     $('#id_peso').val(final);
    //     // Remove motores antigos
    //     $('#itensTableProduto tbody tr').each(function () {
    //         const descricao = $(this).find('td:nth-child(3)').text().toLowerCase().trim();
    //         if (descricao.startsWith('motor')) {
    //             $(this).remove();
    //         }
    //     });
    //     // Cálculo de m²
    //     let larg_corte = parseFloat($('#id_larg_corte').val());
    //     let rolo = parseFloat($('#id_rolo').val().replace(',', '.'));
    //     let alt_corte = parseFloat($('#id_alt_corte').val().replace(',', '.'));
    //     let quantidade = parseFloat($('#id_qtd').val().replace(',', '.'));
    //     if (isNaN(ft_peso) || isNaN(larg_corte) || isNaN(rolo) || isNaN(alt_corte) || isNaN(quantidade)) {
    //         $('#id_m2').val('');
    //         return;
    //     }
    //     calc = ((rolo + alt_corte) * larg_corte) * quantidade;
    //     let aux = arredondarComAjuste(calc);
    //     $('#id_m2').val(aux);
    // }
    // function removerProdutoMotor1500() {
    //     // Lógica para remover o produto motor da tabela
    //     $('#itensTableProduto tr[data-id^="MOTOR 1500KG"]').remove(); // Exemplo de remoção, ajuste conforme necessário
    // }
    let debounceTimeout;
    function atualizarCalculoCompletoDebounced() {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {
            calcFtPeso();
            // calcularValor();
        }, 200);
    }
    $('#id_alt, #id_tp_vao, #id_larg, #id_qtd, #id_rolo, #id_alt_corte, #id_larg_corte').on('blur', atualizarCalculoCompletoDebounced);
    $('#id_desconto, #desconto, #id_acrescimo, #acrescimo').mask('000,000,000,000,000.00', {reverse: true});
    $('#id_vl_prod, #id_vl_prod_adc, #editValorItemInput, #editValorItemAdcInput, .editable, .inpFrete, #id_vl_form_pgto').mask('0000.00', {reverse: true});
    $('#editQtdInput, #editQtdAdcInput, #id_qtd_prod, #id_qtd_prod_adc, #id_alt, #id_alt_corte, #id_larg, #id_rolo, #id_larg_corte, #id_vl_compra').mask('000,000.00', {reverse: true});
    // Função para converter valor em formato brasileiro para float
    var subtotal = 0;
    var desconto = 0;
    var acrescimo = 0;
    var custoTotal = 0;
    var total = 0;
    function atualizarSubtotal() {
        subtotal = 0;
        custoTotal = 0;
        let motorValor = 0;

        $('#itensTableProduto tbody tr, #itensTableProdutoAdc tbody tr').each(function() {
            const valorCompraNumero = parseFloat($(this).find('td:nth-child(8)').text()) || 0;
            const valorNumero = parseFloat($(this).find('td:nth-child(9)').text()) || 0;
            const desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();

            // Caso o item seja um motor, armazene o valor
            if (desc.startsWith('MOTOR')) {
                motorValor += valorCompraNumero;  // ou valorNumero, dependendo do que você precisa
            }

            const largura = parseFloat($('#id_larg').val()) || 0;
            const altura = parseFloat($('#id_alt').val()) || 0;
            if (largura > 0 && altura > 0) custoTotal += valorCompraNumero;
            subtotal += valorNumero;
        });

        // Inclua o valor do motor no subtotal
        subtotal += motorValor;

        // Exibir os resultados
        $('#custoTotal_txt').text('R$ ' + custoTotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $('#subtotal_txt').text('R$ ' + subtotal.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $('#id_subtotal').val(subtotal.toFixed(2));
        $('#id_vl_form_pgto').val(subtotal.toFixed(2));

        desconto = parseFloat($('#id_desconto').val()) || 0;
        acrescimo = parseFloat($('#id_acrescimo').val()) || 0;
        total = subtotal - desconto + acrescimo;

        $('#desconto').text('R$ ' + desconto.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $('#acrescimo').text('R$ ' + acrescimo.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $('#total_txt').text('R$ ' + total.toLocaleString('pt-BR', { minimumFractionDigits: 2 }));
        $('#id_total').val(total.toFixed(2));

        const margemLucro = subtotal > 0 ? ((subtotal - custoTotal) / subtotal) * 100 : 0;
        $('#margem_txt').text(margemLucro.toFixed(2) + '%');
        calcularValorForma();
        somaFormas();
    }

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
    $('#openModalBtn').on('click', function (e) {
        e.preventDefault();
        e.stopPropagation();
        const temPintura = $("#id_pintura").val();
        const corSelecionada = $("#id_cor").val();
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
    // Atualização ao digitar
    $('#id_desconto, #id_acrescimo').on('input', function () {
        atualizarSubtotal();
        calcularValorForma();
        somaFormas();
    });
    class TableManager {
        constructor(tableSelector, hiddenInputSelector, type = 'produto') {
            this.table = $(tableSelector);
            this.hiddenInput = $(hiddenInputSelector);
            this.currentEditingItem = null;
            this.itemCount = this.table.find('tbody tr').length + 1;
            this.type = type; // produto | forma
        }
        addItem(cells, colorIndices = {}) {
            if (!this.currentEditingItem) {
                const cont = String(this.itemCount).padStart(3, '0');
                // monta as células da linha
                const tdHtml = cells.map((val, i) => {
                    let colComp = [3, 6];
                    let colVend = [4, 7];
                    let style = "";

                    if (colComp.includes(i)) {
                        style += "font-weight:bold; color:#DC143C;";
                    }
                    if (colVend.includes(i)) {
                        style += "font-weight:bold; color:#2E8B57;";
                    }

                    // 👉 NOVO: Se for tabela de forma de pagamento, pintar o valor
                    // Ajuste o "i === 1" caso sua coluna de valor seja outra
                    if (this.table.attr('id') === 'itensTableForm' && i === 1) {
                        style += "font-weight:bold; color:#2E8B57;";
                    }

                    if (colorIndices[i]) {
                        style += `color:${colorIndices[i]};`;
                    }

                    return `<td style="${style}">${val}</td>`;
                }).join('');

                // monta os ícones de ação
                let acoes = `<i class="fas fa-trash deleteBtn" style="color:#db1e47;"></i>`;
                // não adiciona editar se for a tabela de forma de pagamento
                if (this.table.attr('id') !== 'itensTableForm') {
                    acoes += `<i class="fas fa-edit editBtn" style="color:#13c43f;"></i>`;
                }
                // adiciona a linha na tabela
                this.table.find('tbody').append(
                    `<tr>
                        <td>${cont}</td>
                        ${tdHtml}
                        <td style="width:80px;">${acoes}</td>
                    </tr>`
                );
                this.itemCount++;
            } else {
                this.updateItem(cells);
            }
            this.updateHiddenInput();
        }
        updateItem(cells) {
            if (!this.currentEditingItem) return;

            // células: [cód, desc, unid, vlUn, qtd]
            const [cod, desc, unid, vlUn, qtd] = cells;

            // obtem valor compra anterior (mantém igual ao original)
            const vlCompra = parseFloat(
                this.currentEditingItem.find('td').eq(4).text().replace(',', '.')
            ) || 0;

            const valorUnit = parseFloat(vlUn.replace(',', '.')) || 0;
            const quantidade = parseFloat(qtd.replace(',', '.')) || 0;

            const totCompra = vlCompra * quantidade;
            const vlTot = valorUnit * quantidade;

            // atualiza colunas conforme estrutura da tabela
            const tds = this.currentEditingItem.find('td');
            tds.eq(1).text(cod);
            tds.eq(2).text(desc);
            tds.eq(3).text(unid);
            tds.eq(5).text(valorUnit.toFixed(2));
            tds.eq(6).text(quantidade.toFixed(2));
            tds.eq(7).text(totCompra.toFixed(2));
            tds.eq(8).text(vlTot.toFixed(2));

            this.currentEditingItem = null;
            this.updateHiddenInput();
            if (typeof atualizarSubtotal === 'function') atualizarSubtotal();
        }

        setEditingItem(row) { this.currentEditingItem = row; }
        deleteItem(button) {
            $(button).closest('tr').remove();
            this.updateHiddenInput();
            atualizarSubtotal();
        }
        updateHiddenInput() {
            const items = this.table.find('tbody tr').map((_, tr) => {
                const tds = $(tr).find('td');
                // se for tabela de formas de pagamento
                if (this.type === 'forma') {
                    if (!tds.eq(1).text()) return null;
                    const valorTexto = tds.eq(2).text().trim();
                    const valorNum = parseValor(valorTexto); // 8.766,78 → 8766.78
                    return {
                        forma: tds.eq(1).text().trim(),
                        valor: valorNum.toFixed(2) // JSON sempre padrão 8766.78
                    };
                }

                // se for tabela de produtos
                if (!tds.eq(1).text()) return null;
                const getNum = idx => parseFloat(tds.eq(idx).text().replace(',', '.')) || 0;
                const vlCompra = getNum(4);
                const vlProd = getNum(5);
                const qtd = getNum(6);
                const prodVlCompraTot = (vlCompra * qtd).toFixed(2);
                const prodVlTot = (vlProd * qtd).toFixed(2);


                return {
                    codProd: tds.eq(1).text().trim(),
                    descProd: tds.eq(2).text().trim(),
                    unidProd: tds.eq(3).text().trim(),
                    vlCompra: vlCompra.toFixed(2),
                    vlProd: vlProd.toFixed(2),
                    qtdProd: qtd.toFixed(2),
                    prodVlCompraTot: prodVlCompraTot,
                    prodVlTot: prodVlTot
                };
            }).get().filter(Boolean);

            const totalGeral = items.reduce((soma, item) => soma + parseFloat(item.prodVlTot || 0), 0);

            this.hiddenInput.val(JSON.stringify(items));
        }

        clearEditing() { this.currentEditingItem = null; }
    }
    // Inicializações
    const formaManager = new TableManager('#itensTableForm', '#id_itens_forma_pgto', 'forma');
    const prodManager = new TableManager('#itensTableProduto', '#id_itens_prod', 'produto');
    const prodAdcManager = new TableManager('#itensTableProdutoAdc', '#id_itens_prod_adc', 'produto');
    // Eventos comuns
    $('#itensTableForm, #itensTableProduto, #itensTableProdutoAdc').on('click', '.deleteBtn', function() {
        const mgr = $(this).closest('table').is('#itensTableForm') ? formaManager : $(this).closest('table').is('#itensTableProduto') ? prodManager : prodAdcManager;
        mgr.deleteItem(this);
    });
    $(document).on('click', '.editBtn', function() {
        const $tr = $(this).closest('tr');

        if ($(this).closest('table').is('#itensTableProduto')) {
            prodManager.setEditingItem($tr);
            $('#editItemModal .modal-title').html(
                `<i class="fa-solid fa-pen-to-square"></i> Edição do Item ${$tr.find('td:eq(0)').text().trim()}`
            );
            $('#editCódInput').val($tr.find('td:eq(1)').text().trim());
            $('#editDescInput').val($tr.find('td:eq(2)').text().trim());
            $('#editUnidInput').val($tr.find('td:eq(3)').text().trim());
            $('#editValorItemInput').val($tr.find('td:eq(5)').text().trim());
            $('#editQtdInput').val($tr.find('td:eq(6)').text().trim());
            const modalEdit = new bootstrap.Modal(document.getElementById('editItemModal'));
            modalEdit.show();

        } else if ($(this).closest('table').is('#itensTableProdutoAdc')) {
            prodAdcManager.setEditingItem($tr); // define o item em edição
            $('#editItemAdcModal .modal-title').html(
                `<i class="fa-solid fa-pen-to-square"></i> Edição do Item ${$tr.find('td:eq(0)').text().trim()}`
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

    $('#saveEditBtn').on('click', function() {
        if (prodManager.currentEditingItem) {
            const cells = [
                $('#editCódInput').val().trim(),
                $('#editDescInput').val().trim(),
                $('#editUnidInput').val().trim(),
                $('#editValorItemInput').val().trim(),
                $('#editQtdInput').val().trim()
            ];
            prodManager.updateItem(cells);
            $('#editItemModal').modal('hide');
            prodManager.clearEditing();
        }
    });

    $('.remQtd').on('click', function() {
        let qtdAtual = parseFloat($('#editQtdInput').val()) || 0;
        if (qtdAtual >= 0) {
            $('#editQtdInput').val(qtdAtual - 1.00);
        }
    });

    $('.addQtd').on('click', function() {
        let qtdAtual = parseFloat($('#editQtdInput').val()) || 0;
        if (qtdAtual >= 0) {
            $('#editQtdInput').val(qtdAtual + 1.00);
        }
    });

    $('.remQtdAdc').on('click', function() {
        let qtdAtual = parseFloat($('#editQtdAdcInput').val()) || 0;
        if (qtdAtual >= 0) {
            $('#editQtdAdcInput').val(qtdAtual - 1.00);
        }
    });

    $('.addQtdAdc').on('click', function() {
        let qtdAtual = parseFloat($('#editQtdAdcInput').val()) || 0;
        if (qtdAtual >= 0) {
            $('#editQtdAdcInput').val(qtdAtual + 1.00);
        }
    });


    $('#saveEditAdcBtn').on('click', function() {
        if (prodAdcManager.currentEditingItem) {
            const cells = [
                $('#editCódAdcInput').val().trim(),
                $('#editDescAdcInput').val().trim(),
                $('#editUnidAdcInput').val().trim(),
                $('#editValorItemAdcInput').val().trim(),
                $('#editQtdAdcInput').val().trim()
            ];
            prodAdcManager.updateItem(cells);
            $('#editItemAdcModal').modal('hide');
            prodAdcManager.clearEditing();
        }
    });
    // Exemplo de adicionar produto/forma (simplificado)
    function addForma(formaPgto, valor) {
        // Exibir na tabela "bonito" (opcional: pt-BR)
        const valorExibicao = valor.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

        formaManager.addItem([
            formaPgto,
            valorExibicao
        ]);

        // Atualizações
        atualizarSubtotal();
        calcularValorForma();
        verificarTotalFormas();
        somaFormas();
    }

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
    $('#addItemValorFormBtn').on('click', function() {
        const formaId = $('#id_formas_pgto').val();
        const valorStr = $('#id_vl_form_pgto').val().trim();
        const valor = parseValor(valorStr);

        if (!formaId) return alert("Selecione uma forma de pagamento");
        if (valor <= 0) return alert("Informe um valor válido");

        // Buscar descrição pelo ID via AJAX
        $.ajax({
            url: "/formas_pgto/get/",
            method: "GET",
            data: { id: formaId },
            success: function(response) {
                addForma(response.descricao, valor);

                // limpa o select2
                $('#id_formas_pgto').val(null).trigger('change');

            },
            error: function() {
                alert("Erro ao buscar a forma de pagamento");
            }
        });

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
    function Calc3() {
        let c3 = 3.6 * 4;
        return c3.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    function recalcularLarguraCorteFinal() {
        // só recalcular se larg e alt existirem
        const larg = $('#id_larg').val().trim();
        const alt  = $('#id_alt').val().trim();
        if (larg === "" || alt === "") return;

        // calcularValor(); // recalcula largura corte, peso e motor
    }
    let lastLg = null;
    let lastAt = null;

    $(document).ready(function() {
        const urlAtual = window.location.href;
        $('#id_larg, #id_alt').on('blur', function () {
            const larg = $('#id_larg').val().trim();
            const alt = $('#id_alt').val().trim();
            if (larg === "" || alt === "") return;
            const lg = parseFloat(larg.replace(',', '.'));
            const at = parseFloat(alt.replace(',', '.'));
            if (lg === lastLg && at === lastAt) {
                console.log("Largura/altura não mudaram — não recalculando.");
                return;
            }
            lastLg = lg;
            lastAt = at;
            resetTable("itensTableProduto", prodManager);
            resetTable("itensTableProdutoAdc", prodAdcManager);
            buscarProdutosPrincipais();
            buscarProdutosAdicionais();
            // calcularValor();
            atualizarTabela();
            atualizarSubtotal();
        });
        $('#prod_servBtn, #adicionaisBtn').on('click', function() {
            const larg = $('#id_larg').val().trim();
            const alt = $('#id_alt').val().trim();
            if (larg === "" || alt === "") {
                console.log("Sem largura/altura — não recalculando.");
                return;
            }
            const lg = parseFloat(larg.replace(',', '.'));
            const at = parseFloat(alt.replace(',', '.'));
            if (lg === lastLg && at === lastAt) {
                console.log("Click sem mudança — não resetando tabelas.");
                return;
            }
            $('#id_larg, #id_alt').blur();
            const temPintura = $("#id_pintura").val();
            if (temPintura === "Não") {
                $('#itensTableProdutoAdc tbody tr').each(function () {
                    const desc = $(this).find('td:nth-child(3)').text().toUpperCase().trim();
                    if (desc === "PINTURA ELETROSTÁTICA" || desc === "PINTURA AUTOMOTIVA") {
                        $(this).remove();
                    }
                });
                atualizarSubtotal();
                calcularValorForma();
                atualizarTabela();
                somaFormas();
                return; // impede que o resto da lógica de pinturas rode
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
                        // Apenas preencher campos desabilitados com texto
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
        const desc = $(this).data('desc');
        const unid = $(this).data('unid');
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
        "Preto": "#000000",
        "Branco": "#FFFFFF",
        "Amarelo": "#FFFF00",
        "Vermelho": "#FF0000",
        "Roxo Açaí": "#6A0DAD",
        "Azul Pepsi": "#0033A0",
        "Azul Claro": "#ADD8E6",
        "Cinza Claro": "#D3D3D3",
        "Cinza Grafite": "#4F4F4F",
        "Verde": "#008000",
        "Bege": "#F5F5DC",
        "Bege Areia": "#D7C9A3",
        "Marrom": "#8B4513",
        "Marrom Café": "#4B2E2B",
        "Laranja": "#FFA500",
        "Azul Royal": "#4169E1",
        "Azul Marinho": "#000080",
        "Verde Musgo": "#556B2F",
        "Verde Bandeira": "#009739",
        "Vinho": "#8B0000",
        "Prata": "#C0C0C0"
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
        console.log("Função atualizarCampo() executada");
        let tipoPessoa = $("#id_pessoa").val();
        console.log("Tipo de pessoa:", tipoPessoa);
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

    $(document).ready(function () {
        atualizarCampo(); // Executa ao carregar a página com valor existente
        $("#id_pessoa").change(atualizarCampo); // Executa ao mudar o valor
        mudarCampoChavePix();
        $("#id_tp_chave").change(mudarCampoChavePix);
    });
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
            // Se tiver mais que 11 dígitos, garante o formato correto
            r = r.replace(/^(\d{2})(\d{5})(\d{4}).*/, "($1) $2-$3");
        } else if (r.length === 11) {
            // Celular (com 9 dígitos no número)
            r = r.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
        } else if (r.length === 10) {
            // Telefone fixo (com 8 dígitos no número)
            r = r.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");
        } else if (r.length > 2) {
            // Apenas DDD digitado, começando a formatar o número
            r = r.replace(/^(\d{2})(\d{0,5})/, "($1) $2");
        } else if (r.length > 0) {
            // Apenas o primeiro número (abrindo o parêntese do DDD)
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
            // Condição para números com o terceiro dígito sendo 8 ou 9
            if (cleanedPhone[2] === '8' || cleanedPhone[2] === '9') {
                cleanedPhone = cleanedPhone.slice(0, 2) + '9' + cleanedPhone.slice(2);
                return cleanedPhone.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
            }
            // Nova condição para números com o terceiro dígito sendo 4, 5 ou 6
            else if (cleanedPhone[2] === '4' || cleanedPhone[2] === '5' || cleanedPhone[2] === '6') {
                return cleanedPhone.replace(/^(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
            }
        }
        return cleanedPhone.replace(/^(\d{2})(\d{4,5})(\d{4})$/, '($1) $2-$3');
    }
    function formatarTelefone(ddd, numero) {
        let telefone = ddd + numero;
        telefone = telefone.replace(/\D/g, ""); // Remove caracteres não numéricos
        if (telefone.length === 10) {
            return telefone.replace(/^(\d{2})(\d{4})(\d{4})$/, "($1) $2-$3");
        } else if (telefone.length === 11) {
            return telefone.replace(/^(\d{2})(\d{5})(\d{4})$/, "($1) $2-$3");
        }
        return telefone;
    }
    $("#id_cpf_cnpj").on("blur", function () {
        let tipoPessoa = $("#id_pessoa").val();
        let cnpj = $(this).val().replace(/\D/g, ""); // Remove caracteres não numéricos
        // Verifica se está no modo CNPJ e se o campo tem 14 números
        if (tipoPessoa === "Jurídica" && cnpj.length === 14) {
            $('#loadingModal').modal('show');
            fetch(`https://open.cnpja.com/office/${cnpj}`)
                .then(response => response.json())
                .then(data => {
                    console.log(data);
                    // Razão Social e Fantasia
                    if (data.company) {
                        $('#id_razao_social').val((data.company.name || "").toUpperCase());
                        $('#id_fantasia').val((data.alias || "").toUpperCase());
                    }
                    // Inscrição Estadual
                    if (data.registrations && data.registrations.length > 0) {
                        let ieNumber = data.registrations[0].number || "";
                        if (data.registrations[0].state === "PA") {
                            ieNumber = ieNumber.replace(/^(\d{2})(\d{3})(\d{3})(\d{1})$/, '$1.$2.$3-$4');
                        }
                        $('#id_ie').val(ieNumber);
                    }
                    // CEP
                    let cep = (data.address?.zip || "").replace(/^(\d{5})(\d{3})$/, '$1-$2');
                    $('#id_cep').val(cep);
                    // Endereço abreviado
                    let endereco = (data.address?.street || "").toUpperCase();
                    $('#id_endereco').val(abreviarEndereco(endereco));
                    $('#id_numero').val(data.address?.number || "");
                    // Estado, Cidade e Bairro
                    let estado = (data.address?.state || "").toUpperCase();
                    let cidade = (data.address?.city ? removeAccents(data.address.city) : "").toUpperCase();
                    let bairro = (data.address?.district || "").toUpperCase();
                    // Verifica e atualiza os campos Select2
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
                    // Telefone
                    if (data.phones && data.phones.length > 0) {
                        let telefone = (data.phones[0].area || "") + " " + (data.phones[0].number || "");
                        $('#id_tel').val(mascaraFone(telefone));
                    }
                    // Email
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
    var form = $('#createForm');
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
        var loadingModal = new bootstrap.Modal($("#loadingModal")[0]);
        // Fecha o modal de menu antes de exibir o spinner
        if (menuModal) {
            menuModal.hide();
        }
        if (docModal) {
            docModal.hide();
        }
    });
    $("#confirmBtn").on("click", function () {
        setTimeout(function () {
            var loadingModal = new bootstrap.Modal($("#loadingModal")[0]);
            loadingModal.show();
        }, 300);
        form.submit();
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
        return parseFloat(str.replace('R$ ', '').replace(/,/g, '').trim()) || 0;
    }
    // Função de cálculo do desconto e atualização do auxiliar
    function calcularDescontoAtualizarAuxiliar() {
        let tipo_desconto = $('#tipo_desconto').val();
        let campoDigitado = $('#campo_desconto').val().replace(',', '.');
        let campo_desconto = parseFloat(campoDigitado);

        // Se estiver digitando algo como "1," não trava e assume o número antes da vírgula
        if (isNaN(campo_desconto)) {
            campo_desconto = parseFloat(campoDigitado.replace('.', '')) || 0;
        }

        let subtotal_orcamento = extrairNumero($('#subtotal_txt').text());
        let labelNomeCampo = $("label[for='campo_desconto']");
        let labelNomeCampoAuxiliar = $("label[for='auxiliar_desconto']");
        let simboloInputCampo = $("#simbolo");
        let simboloInputCampoAuxiliar = $("#simboloAuxiliar");

        if (subtotal_orcamento === 0) {
            $('#auxiliar_desconto').val('');
            return 0;
        }

        if (tipo_desconto === "valor") {
            labelNomeCampo.text("Valor:");
            simboloInputCampo.text("R$");
            labelNomeCampoAuxiliar.text("Percentual:");
            simboloInputCampoAuxiliar.text("%");

            desconto_aplicado = campo_desconto;
            let percentual = ((desconto_aplicado / subtotal_orcamento) * 100).toFixed(2);

            $('#auxiliar_desconto').val(isNaN(percentual) ? '' : percentual);

            return desconto_aplicado; // 👈 OBRIGATÓRIO
        } else {
            // CAMPO PRINCIPAL = %
            labelNomeCampo.text("Percentual:");
            simboloInputCampo.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliar.text("R$");

            let valorCalculado = ((subtotal_orcamento * campo_desconto) / 100);

            if (!isNaN(valorCalculado))
                $('#auxiliar_desconto').val(valorCalculado.toFixed(2));
            else
                $('#auxiliar_desconto').val('');
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

        // Se vier undefined, null, NaN → vira 0
        desconto = parseFloat(desconto) || 0;

        // Atualiza o campo de input
        $('#id_desconto').val(desconto.toFixed(2));

        $('#desconto_txt').text('R$ ' + desconto.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }));

        $('#modalDesconto').modal('hide');
        atualizarSubtotal();
    });
    // Função de Acréscimo - Orçamentos
    // Função de cálculo do acrescimo e atualização do auxiliar
    function calcularAcrescimoAtualizarAuxiliar() {
        let tipo_acrescimo = $('#tipo_acrescimo').val();
        let campo_acrescimo = parseFloat($('#campo_acrescimo').val().replace(',', '.')) || 0;
        let subtotal_orcamento = extrairNumero($('#subtotal_txt').text());
        let acrescimo_aplicado = 0;
        let labelNomeCampo = $("label[for='campo_acrescimo']");
        let labelNomeCampoAuxiliar = $("label[for='auxiliar_acrescimo']");
        let simboloInputCampoAc = $("span[id='simboloAc']");
        let simboloInputCampoAuxiliarAc = $("span[id='simboloAuxiliarAc']");
        if (subtotal_orcamento === 0) {
            $('#auxiliar_acrescimo').val('');
            return 0;
        }
        if (tipo_acrescimo === "valor") {
            labelNomeCampo.text("Valor:");
            simboloInputCampoAc.text("R$");
            labelNomeCampoAuxiliar.text("Percentual:");
            simboloInputCampoAuxiliarAc.text("%");
            acrescimo_aplicado = campo_acrescimo;
            let percentual = ((acrescimo_aplicado / subtotal_orcamento) * 100).toFixed(2);
            $('#auxiliar_acrescimo').val(isNaN(percentual) ? '' : percentual);
        } else {
            labelNomeCampo.text("Percentual:");
            simboloInputCampoAc.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliarAc.text("R$");
            acrescimo_aplicado = ((subtotal_orcamento * campo_acrescimo) / 100).toFixed(2);
            $('#auxiliar_acrescimo').val(isNaN(acrescimo_aplicado) ? '' : acrescimo_aplicado);
            $('#auxiliar_acrescimo').css('color', '');
        }
        return parseFloat(acrescimo_aplicado);
    }
    // Quando muda o tipo de acrescimo
    $('#tipo_acrescimo').on('change', function() {
        calcularAcrescimoAtualizarAuxiliar();
    });
    // Quando digita no campo de valor ou percentual
    $('#campo_acrescimo').on('input change', function() {
        calcularAcrescimoAtualizarAuxiliar();
    });
    // Evento ao abrir o modal
    $('#modalAcrescimo').on('shown.bs.modal', function () {
        $('#tipo_acrescimo').focus();
    });
    // Evento botão confirmar
    $('#confirmarAcrescimo').on('click', function () {
        let acrescimo = calcularAcrescimoAtualizarAuxiliar();
        // Atualiza o campo de input (se desejar manter)
        $('#id_acrescimo').val(acrescimo.toFixed(2));
        // Atualiza o texto visível
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
    function buscarCoordenadas(cidade) {
        if (!cidade) {
            return;
        }
        const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cidade)}&format=json&limit=1`;
        $.get(url, function(dados) {
            if (dados.length > 0) {
                const latitude = dados[0].lat;
                const longitude = dados[0].lon;
                $('#id_latitude').val(latitude);
                $('#id_longitude').val(longitude);
                console.log(`Coordenadas de ${cidade}: Latitude ${latitude}, Longitude ${longitude}`);
            } else {
                console.log("Não foi possível encontrar as coordenadas para essa cidade.");
            }
        }).fail(function() {
            console.error("Erro ao consultar a API de geolocalização.");
        });
    }
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
    function previewImage(event) {
        var reader = new FileReader();
        reader.onload = function() {
            var output = $('#logo-preview');
            output.src = reader.result; // Atualiza a imagem de visualização
        };
        reader.readAsDataURL(event.target.files[0]);
    }
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
            // mostra apenas o nome após selecionar
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
            // Condição para números com o terceiro dígito sendo 8 ou 9
            if (cleanedPhone[2] === '8' || cleanedPhone[2] === '9') {
                cleanedPhone = cleanedPhone.slice(0, 2) + '9' + cleanedPhone.slice(2);
                return cleanedPhone.replace(/^(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
            }
            // Nova condição para números com o terceiro dígito sendo 4, 5 ou 6
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
    // Seções do formulário de Empresas
    var endSecao = $('#enderecos');
    var compSecao = $('#complementos');
    var dadosRespSecao = $('#dadosResponsavel');
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
    var medidasSecao = $('#medidas');
    var clienteSecao = $('#clientes');
    var prod_servSecao = $('#prod_serv');
    var adicionaisSecao = $('#adicionais');
    var form_pgtoSecao = $('#form_pgto');
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
    $(document).ready(function() {
        // Se existe a seção de orçamentos, mostra a padrão dela
        if ($('#medidas').length > 0) {
            showSection('medidas', medidasBtn, clienteBtn, prod_servBtn, adicionaisBtn, form_pgtoBtn);
        }
        // Se existe a seção de empresas, mostra a padrão dela
        if ($('#enderecos').length > 0) {
            showSection1('enderecos', endBt, compBt);
        }
    });
    $(document).on('click', '#info-icon', function() {
        var orderId = $(this).data('id');
        listarOrdensServico(orderId);
    });
    $('#id_serial, #id_nome_empresa, #id_nome_emp, #id_desc_prod').focus();
    $('#loadingModal').modal({
        keyboard: true,
        backdrop: 'static'});
    function normalize(text) {
      return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "");}
    $('#cliente, #id_cli').select2({
        placeholder: 'Selecione um cliente',
        allowClear: true,
        minimumInputLength: 1,
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
            // Prevenir o envio do formulário
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
    function formatarDataParaBackend(dataInput) {
      const partes = dataInput.split('-');
      return `${partes[2]}-${partes[1]}-${partes[0]}`;

    }
    const dataPesquisaInput = $("#data_pesquisa");
    // Obtenha a data atual no formato correto para o campo de entrada de data
    const today = new Date().toISOString().slice(0, 10);
    // Defina o valor do campo de entrada para a data atual
    dataPesquisaInput.val(today);
});
