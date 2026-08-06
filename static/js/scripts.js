$(document).ready(function() {
    let portaDetalhes = {};
    let portaFotos = {};
    let fotosRemover = [];
    // Kanban
    function alterarStatus(codigo,status){
        $.ajax({
            url:"/orcamentos/ajax/alterar_status_k/",
            type:"POST",
            data:{
                codigo:codigo,
                status:status,
                csrfmiddlewaretoken:$("[name=csrfmiddlewaretoken]").val()
            },
            success:function(){
                atualizarTotais();
            }
        });
    }
    $(document).on("click",".kanban-card",function(e){
        if($(e.target).closest(".dropdown").length)
            return;
        let codigo=$(this).data("codigo");
        location.href="/orcamentos/att/"+codigo+"/";
    });
    $(".kanban-coluna").each(function(){
        new Sortable(this,{
            group:'orcamentos',
            animation:150,
            ghostClass:'bg-warning',
            onEnd:function(evt){
                let codigo=$(evt.item).data("codigo");
                let status=$(evt.to).data("status");
                alterarStatus(codigo,status);
            }
        });
    });
    // UPLOAD DE FOTOS
    function renderFotosPorta(porta){
        const lista = $(".lista-fotos");
        lista.find(".foto-item").remove();
        if(!portaFotos[porta])
            portaFotos[porta]=[];
        portaFotos[porta].forEach(function(foto,indice){
            let src="";
            if(foto.file){src = URL.createObjectURL(foto.file);}
            else{src = foto.url;}
            const item=$(`
                <div class="foto-item" data-index="${indice}">
                    <img src="${src}">
                    <button type="button" class="remover-foto"><i class="fas fa-trash text-white"></i></button>
                </div>
            `);
            lista.find(".foto-add").before(item);
        });
    }
    $(document).on("click", ".foto-add", function () {$(this).closest(".upload-fotos").find(".input-fotos").click();});
    $(document).on("change",".input-fotos",function(){
        const porta=$("#modalPortaId").val();
        if(!portaFotos[porta])
            portaFotos[porta]=[];
        $.each(this.files,function(_,arquivo){
            portaFotos[porta].push({file:arquivo, preview:URL.createObjectURL(arquivo), id:null, principal:false, ordem:portaFotos[porta].length, novo:true});
            renderFotosPorta(porta);
        });
        $(this).val("");
        renderFotosPorta(porta);
    });
    $(document).on("click",".remover-foto",function(e){
        e.preventDefault();
        e.stopPropagation();
        const porta=$("#modalPortaId").val();
        const indice=Number($(this).closest(".foto-item").data("index"));
        const foto=portaFotos[porta][indice];
        if(foto.file){URL.revokeObjectURL(card.find("img").attr("src"));}
        if(foto.novo && foto.preview)
            URL.revokeObjectURL(foto.preview);
        if(foto.id)
            fotosRemover.push(foto.id);
        portaFotos[porta].splice(indice,1);
        renderFotosPorta(porta);
    });
    // Método de leitura de Certificado Digital
    $(function () {
        if (!window.FILIAL_CONFIG) {
            console.warn("Não achei a FILIAL_CONFIG");
            return;
        }
        console.log("FILIAL_CONFIG:", window.FILIAL_CONFIG);
        if (window.FILIAL_CONFIG.temCertificado) {validarCertificadoSalvo();}
        function validarCertificadoSalvo() {
            $('#info-certificado').html(`
                <div class="card shadow-sm">
                    <div class="card-body text-center py-4">
                        <div class="spinner-border text-primary"></div>
                        <div class="mt-2">Validando certificado salvo...</div>
                    </div>
                </div>
            `);
            $.ajax({
                url: `/filiais/${window.FILIAL_CONFIG.codigo}/validar-certificado-salvo/`, type: "GET",
                success: function(r){
                    if(!r.ok){
                        $('#info-certificado').html(`<div class="alert alert-danger">${r.erro}</div>`);
                        return;
                    }
                    let cor = "success";
                    let icone = "fa-check-circle";
                    let titulo = "Certificado válido";
                    if (r.vencido) {
                        cor = "danger";
                        icone = "fa-times-circle";
                        titulo = "Certificado vencido";
                    }
                    else if (r.vence_breve) {
                        cor = "warning";
                        icone = "fa-exclamation-triangle";
                        titulo = "Certificado próximo do vencimento";
                    }
                    $('#info-certificado').html(`
                        <div class="card border-${cor} shadow-sm">
                            <div class="card-header bg-${cor} text-white">
                                <h5 class="mb-0"><i class="fas ${icone}"></i> ${titulo}</h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6"><b>Titular</b><br> ${r.titular}</div>
                                    <div class="col-md-6"><b>CNPJ</b><br> ${r.cnpj_formatado}</div>
                                    <div class="col-md-4 mt-3"><b>Início</b><br> ${r.inicio_validade}</div>
                                    <div class="col-md-4 mt-3"><b>Validade</b><br> ${r.fim_validade}</div>
                                    <div class="col-md-4 mt-3"><b>Dias Restantes</b><br> ${r.dias_restantes}</div>
                                </div>
                            </div>
                        </div>
                    `);
                }
            });
        }
        function validarCertificado() {
            let arquivo = $('#id_certificado')[0].files[0];
            let senha = $('#id_senha_certificado').val();
            if (!arquivo)
                return;
            if (!senha) {
                toast("Informe a senha do certificado para validar!", "warning");
                return;
            }
            let dados = new FormData();
            dados.append('certificado', arquivo);
            dados.append('senha', senha);
            let cnpj = $('#id_cnpj').val().replace(/\D/g,'');
            dados.append('cnpj_filial', cnpj);
            $('#info-certificado').html(`
                <div class="card shadow-sm">
                    <div class="card-body text-center py-4">
                        <div class="spinner-border text-primary"></div>
                        <div class="mt-2">Lendo certificado...</div>
                    </div>
                </div>
            `);
            $.ajax({
                url: "/filiais/validar-certificado/", type: "POST", data: dados, processData: false, contentType: false,
                headers: {"X-CSRFToken": $('[name=csrfmiddlewaretoken]').val()},
                success: function (r) {
                    if (!r.ok) {
                        toast(`${r.erro}`, "error");
                        return;
                    }
                    let cor = "success";
                    let icone = "fa-check-circle";
                    let titulo = "Certificado válido";
                    if (r.vencido) {
                        cor = "danger";
                        icone = "fa-times-circle";
                        titulo = "Certificado vencido";
                    }
                    else if (r.vence_breve) {
                        cor = "warning";
                        icone = "fa-exclamation-triangle";
                        titulo = "Certificado próximo do vencimento";
                    }
                    if (r.cnpj && !r.cnpj_ok) {
                        $('#id_certificado').val('');
                        $('#id_senha_certificado').val('');
                        $('#info-certificado').html(`
                            <div class="alert alert-danger">
                                <h5><i class="fas fa-ban"></i> CNPJ incompatível</h5>
                                <hr>
                                <b>CNPJ da Filial:</b><br>
                                ${$('#id_cnpj').val()}<br><br>
                                <b>CNPJ do Certificado:</b><br>
                                ${r.cnpj_formatado}
                            </div>
                        `);
                        return;
                    }
                    $('#info-certificado').html(`
                        <div class="card border-${cor} shadow-sm">
                            <div class="card-header bg-${cor} text-white">
                                <h5 class="mb-0"><i class="fas ${icone}"></i> ${titulo}</h5>
                            </div>
                            <div class="card-body">
                                <div class="row">
                                    <div class="col-md-6"><b>Titular</b><br> ${r.titular}</div>
                                    <div class="col-md-6"><b>CNPJ</b><br> ${r.cnpj_formatado}</div>
                                    <div class="col-md-4 mt-3"><b>Início</b><br> ${r.inicio_validade}</div>
                                    <div class="col-md-4 mt-3"><b>Validade</b><br> ${r.fim_validade}</div>
                                    <div class="col-md-4 mt-3"><b>Dias Restantes</b><br> ${r.dias_restantes}</div>
                                </div>
                            </div>
                        </div>
                    `);
                },
                error: function () {toast("Erro ao validar o certificado!", "error");}
            });
        }
        $('#id_certificado').on('change', validarCertificado);
        $('#id_senha_certificado').on('change blur', validarCertificado);
    });
    // Mostrar/ocultar campos de Formas, Filiais e Tabelas
    function cardUsuario(select, card) {
        if (select.val() === '0') {card.removeClass('d-none');}
        else {card.addClass('d-none');}
    }
    cardUsuario($('#id_opfilial'), $('.card-filiais'));
    cardUsuario($('#id_opformas'), $('.card-formas'));
    cardUsuario($('#id_optabelas'), $('.card-tabelas'));
    $('#id_opfilial').on('change', function () {cardUsuario($(this), $('.card-filiais'));});
    $('#id_opformas').on('change', function () {cardUsuario($(this), $('.card-formas'));});
    $('#id_optabelas').on('change', function () {cardUsuario($(this), $('.card-tabelas'));});
    //
    $('.mb-3').removeClass('mb-3');
    $('#id_alterar_senha').on('change', function () {
        $('#id_password').prop('readonly', !this.checked);
        if (this.checked) {$('#id_password').css('background-color', 'white');}
        else {$('#id_password').css('background-color', '#A9A9A9');}
    });
    $('label[for="id_alterar_senha"]').on('click', function () {
        setTimeout(function () {
            $('#id_password').prop('readonly', !this.checked).prop('checked');
        }, 0);
    });
    $('[id^="colCancelar"]').on('shown.bs.collapse', function () {$(this).find('[id^="motivoCancelamento"]').val('').focus();});
    let REGRAS = {};
    let DADOS_FILIAL = {};
    let logoPreviewUrl = null;
    $('#logo-preview').on('click', function () {$('#id_logo').click();});
    $('#id_logo').on('change', function () {
        if (!this.files.length) return;
        if (logoPreviewUrl) {URL.revokeObjectURL(logoPreviewUrl);}
        logoPreviewUrl = URL.createObjectURL(this.files[0]);
        $('#logo-preview').attr('src', logoPreviewUrl);
    });
    let fotoPreviewUrl = null;
    $('#foto-preview').on('click', function () {$('#id_foto').click();});
    $('#id_foto').on('change', function () {
        if (!this.files.length) return;
        if (fotoPreviewUrl) {URL.revokeObjectURL(fotoPreviewUrl);}
        fotoPreviewUrl = URL.createObjectURL(this.files[0]);
        $('#foto-preview').attr('src', fotoPreviewUrl);
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
                Multi Lg. Corte: ${f.multi_lg_corte ?? '-'}
                Tabela Preço: ${f.tb_preco ?? '-'}
                Ag. Itens: ${f.agrupa_itens}
                Multi Qtde. Lâm: ${f.mt_qt_lam}
                `).join('\n\n');
            console.log(texto);
            console.log("DADOS_FILIAL:", DADOS_FILIAL);
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
                const novoVl   = parseBR(cells[3]) || 0;
                const novaQtd  = parseBR(cells[4]);
                const mudou = item.cod !== novoCod || item.desc !== novaDesc || item.unid !== novaUnid || item.vl_unit !== novoVl || (!isNaN(novaQtd) && Number(item.qtd_final ?? 0) !== novaQtd);
                if (!mudou) return;
                item.cod = novoCod; item.desc = novaDesc;
                item.unid = novaUnid; item.vl_unit = novoVl;
                if (!isNaN(novaQtd)) {
                    item.qtd_final  = novaQtd;
                    item.qtd_manual = true;
                    item.ativo      = novaQtd > 0;
                }
                $tr.find('.cod-div').text(item.cod);
                $tr.find('.desc-div').text(item.desc);
                $tr.find('.unid-div').text(item.unid);
                $tr.find('.vl-u-div').text(formatBR(item.vl_unit));
                $tr.find('.qtd-div').text(formatBR(item.qtd_final));
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
        const fmt = v => formatBR(v || 0);
        const totCompra = (item.qtd_final * item.vl_compra);
        const vlTotal   = (item.qtd_final * item.vl_unit);
        const regraAttr = regraOrigem ? `data-regra-origem="${regraOrigem}"` : '';
        return `
            <div class="list-group-item py-1 item-lista" data-porta="${porta}" data-item-id="${item.id}" ${regraAttr}>
                <div class="row align-items-center linha-lista">
                    <!-- Código -->
                    <div class="col-md-1 fw-bold codigo-col cod-div text-secondary" data-label="Código:">#${item.cod}</div>
                    <!-- Descrição -->
                    <div class="col-md-4 fw-semibold descricao-col desc-div" data-label="Descrição:">${item.desc}</div>
                    <!-- Unidade -->
                    <div class="col-md-1 fw-semibold codigo-col unid-div" data-label="Unidade:">${item.unid}</div>
                    <!-- Valor Compra -->
                    <div class="col-md-1 fw-semibold codigo-col vl-c-div text-danger" data-label="Vl. Custo:">${fmt(item.vl_compra)}</div>
                    <!-- Valor Unitário -->
                    <div class="col-md-1 fw-semibold codigo-col vl-u-div text-success" data-label="Vl. Unit.:">${fmt(item.vl_unit)}</div>
                    <!-- Quantidade -->
                    <div class="col-md-1 fw-semibold codigo-col qtd-div" data-label="Qtde.:">${fmt(item.qtd_final)}</div>
                    <!-- Total Compra -->
                    <div class="col-md-1 fw-semibold codigo-col tot-c-div text-danger" data-label="Tot. Custo:">${fmt(totCompra)}</div>
                    <!-- Total Venda -->
                    <div class="col-md-1 fw-semibold codigo-col tot-v-div text-success" data-label="Tot. Venda:">${fmt(vlTotal)}</div>
                    <!-- Ações -->
                    <div class="col-md-1 mb-1 mb-md-0 acoes-col">
                        <div class="btn-group btn-group-sm">
                            <button type="button" class="btn btn-light btn-sm border editBtn" data-bs-target="#${modalEditar}"><i class="fa-regular fa-pen-to-square text-success"></i></button>
                            <button type="button" class="btn btn-light btn-sm border deleteBtn"><i class="fa-solid fa-trash-can text-danger"></i></button>
                        </div>
                    </div>
                </div>
            </div>
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
    hidratarFotos(portasJSON);
    hidratarDetalhes(portasJSON);
    calcTotalEntrada();
    calcTotalPedido();
    $('.table').addClass("table-sm");
    $('[name^="nome_"]').first().focus();
    $('[name^="descricao"]').first().focus();
    function parseBR(valor) {
        if (valor === null || valor === undefined || valor === '') return 0;
        let s = String(valor).trim();
        s = s.replace(/R\$\s?/g, '').replace(/\s/g, '');
        const temVirgula = s.includes(',');
        const temPonto = s.includes('.');
        if (temVirgula && temPonto) {
            if (s.lastIndexOf(',') > s.lastIndexOf('.')) {s = s.replace(/\./g, '').replace(',', '.');}
            else {s = s.replace(/,/g, '');}
        }
        else if (temVirgula) {s = s.replace(',', '.');}
        const num = parseFloat(s);
        return isNaN(num) ? 0 : num;
    }
    function formatBR(valor, casas = 2) {
        const num = parseBR(valor);
        return num.toLocaleString('pt-BR', {minimumFractionDigits: casas, maximumFractionDigits: casas});
    }
    function formatInputBR(valor, casas = 2) {
        const num = parseBR(valor);
        return num.toFixed(casas).replace('.', ',');
    }
    function aplicarMascaraMoney(input) {
        if (!input) return;
        let valor = '';
        if (typeof input === 'object' && input.value !== undefined) {valor = input.value;}
        else {valor = String(input);}
        valor = valor.replace(/\D/g, '');
        if (!valor) {
            if (typeof input === 'object' && input.value !== undefined) {input.value = '0,00';}
            return '0,00';
        }
        let num = parseInt(valor, 10) / 100;
        let formatado = num.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
        if (typeof input === 'object' && input.value !== undefined) {input.value = formatado;}
        return formatado;
    }
    // Teste para Abertura de Caixa
    $(function () {
        const $container = $('#formas-container');
        if (!$container.length) return; // 🔥 não está na tela
        if (typeof FORMAS === 'undefined') return;
        FORMAS.forEach(f => {
            $container.append(`
                <div class="col-md-3 mb-2">
                    <label>${f.descricao}</label>
                    <input type="text" name="forma_${f.codigo}" class="form-control form-control-sm text-end fw-bold money" value="0,00">
                </div>
            `);
        });
    });
    //Teste de Caixa
    let itens = [];
    let editIndex = null;
    let cliente = null;
    let vendedor = null;
    let tabelaPreco = null;
    let AGRUPA_ITENS = false;
    let descontoGeral = {tipo: null, valor: 0, operacao: null};
    function initDadosVenda(filialId) {
        console.log("Recebi:", filialId);
        const filialAtual = DADOS_FILIAL[String(filialId)];
        console.log("filialAtual:", filialAtual);
        if (!filialAtual) {
            console.error("Não achei a filial");
            return;
        }
        AGRUPA_ITENS = !!filialAtual.agrupa_itens;
        cliente = filialAtual.cli ? {id: filialAtual.cli, nome: filialAtual.cli_nome} : null;
        vendedor = filialAtual.vend ? {id: filialAtual.vend, nome: filialAtual.vend_nome} : null;
        tabelaPreco = filialAtual.tb_preco ? {id: filialAtual.tb_preco, nome: filialAtual.tb_preco_nome} : null;
        console.log(cliente);
        console.log(vendedor);
        console.log(tabelaPreco);
        atualizarResumoVenda();
    }
    carregarDadosFilial().then(() => {
        console.log("FILIAL_ID:", FILIAL_ID);
        console.log("FILIAL:", DADOS_FILIAL[String(FILIAL_ID)]);
        initDadosVenda(FILIAL_ID);
    });
    function atualizarHora() {
        const agora = new Date();
        const hora = agora.toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
        $('#horaAtual').text(hora);
    }
    // roda imediatamente
    atualizarHora();
    // atualiza a cada 1 segundo
    setInterval(atualizarHora, 1000);
    /* 🔎 BUSCA PRODUTO (SEU SCRIPT) */
    $(window).on('load', function () {
        setTimeout(() => {
            const $input = $('#id_cod_produtoCaixa');
            if (!$input.length) return;
            $('#id_quantidadeP').val('1,00');
            $input.val('').focus();
        }, 500);
    });
    /* ENTER ADICIONA */
    buscarProdutoCaixa({
        inputCod: '#id_cod_produtoCaixa', desc: '#id_desc_prodCaixa', marca: '#id_marcaProdCaixa', unid: '#id_unidProdutoCaixa', grupo: '#id_grupoProdCaixa',
        preco: '0,00', precoVenda: '#id_preco_unitCaixa', focoFinal: '#id_quantidadeCaixa',
        aposCarregar: function () {
            calcularTotal();
            // 🔥 adiciona automaticamente no Enter
            if (window.enterPressionado) {
                window.enterPressionado = false;
                setTimeout(() => {
                    $('#btnAddProduto').click();
                }, 50);
            }
        }
    });
    window.enterPressionado = false;
    $('#id_cod_produtoCaixa').on('keydown', function(e){
        if(e.key === 'Enter'){
            e.preventDefault();
            let valor = $(this).val().trim();
            // 🔥 padrão: qtd*codigo
            if(valor.includes('*')){
                let partes = valor.split('*');
                let qtd = partes[0].replace(',', '.').trim();
                let cod = partes[1]?.trim();
                qtd = parseBR(qtd);
                // 🔥 se quantidade válida
                if(!isNaN(qtd) && cod){
                    $('#id_quantidadeCaixa').val(formatBR(qtd));
                    $(this).val(cod);
                }
            }
            window.enterPressionado = true;
            $(this).trigger('blur');
        }
    });
    let adicionandoPorEnter = false;
    $('#id_cod_produtoCaixa').on('keydown', function(e){
        if(e.key === 'Enter'){adicionandoPorEnter = true;}
    });
    $('#id_cod_produtoCaixa').on('blur', function(){
        if(adicionandoPorEnter){
            adicionandoPorEnter = false;
            return;
        }
        setTimeout(() => {
            let produto = $('#id_cod_produtoCaixa').val();
            let desc = $('#id_desc_prodCaixa').val();
            if(produto && desc){$('#btnAddProduto').click();}
        }, 200);
    });
    /* ADD ITEM */
    $('#btnAddProduto').click(function () {
        let item = {produto_id: $('#id_cod_produtoCaixa').val(), desc: $('#id_desc_prodCaixa').val(), qtd: parseBR($('#id_quantidadeCaixa').val()),
            preco: parseBR($('#id_preco_unitCaixa').val()), total: 0, ajuste: 0, tipo_ajuste: null
        };
        if (!item.produto_id || item.qtd <= 0) return;
        item.total = item.qtd * item.preco;
        if (editIndex !== null) {
            itens[editIndex] = item;
            editIndex = null;
        } else {
            if (AGRUPA_ITENS) {
                let existente = itens.find(i => i.produto_id == item.produto_id && i.preco == item.preco && !i.tipo_ajuste);
                if (existente) {
                    existente.qtd += item.qtd;
                    existente.total = existente.qtd * existente.preco;
                }
                else {itens.push(item);}
            }
            else {itens.push(item);}
        }
        aplicarDescontoGeral(); // 🔥 reaplica se existir
        renderItens();
        limparCampos();
        $('#id_quantidadeCaixa').val('1,00');
        $('#id_desc_prodCaixa').val(item.desc);
    });
    /* 🔥 FUNÇÃO ADICIONAL PARA INJETAR ITENS DE DEVOLUÇÃO DO MODAL NO CARRINHO */
    function adicionarItemAoCarrinhoCaixa(itemDevolucao) {
        // Monta o objeto exatamente no formato que o seu array 'itens' e a função 'renderItens()' utilizam
        let item = {
            produto_id: String(itemDevolucao.codigo_produto), desc: itemDevolucao.descricao, qtd: parseBR(itemDevolucao.quantidade), preco: parseBR(itemDevolucao.vl_unit),
            total: parseBR(itemDevolucao.subtotal), ajuste: 0, tipo_ajuste: null, is_devolucao: true, item_pedido_id: itemDevolucao.item_pedido_id
        };
        // Regra de segurança: Não agrupa itens de devolução para não misturar as referências das linhas originais
        itens.push(item);
        // Executa as mesmas funções que o seu botão original executa
        aplicarDescontoGeral(); // Reaplica descontos se houver
        renderItens();          // Atualiza o grid do caixa e recalcula o total automaticamente
        limparCampos();         // Devolve o foco para o leitor de código de barras
    }
    $('#btn-js').click(function () {iniciarLoading();});
    let totalBase = 0;
    $(document).on('click', '#modalOpções .menu-opcao', function (e) {
        const acao = $(this).data('acao');
        const validarAcoes = ['atribuir_desconto_ped', 'atribuir_acrescimo_ped'];
        if (validarAcoes.includes(acao)) {
            const semItens = !itens || itens.length === 0;
            if (semItens) {
                e.preventDefault();
                e.stopImmediatePropagation();
                toast(`Adicione produtos para aplicar desconto ou acréscimo!`, "warning");
                $('.item-lista').addClass('border border-warning');
                setTimeout(() => {
                    $('.item-lista').removeClass('border border-warning');
                }, 1500);
                return false;
            }
        }
        if (acao === 'atribuir_desconto_ped') {abrirModalDesconto('desconto');}
        if (acao === 'atribuir_acrescimo_ped') {abrirModalDesconto('acrescimo');}
    });
    function abrirModalDesconto(operacao) {
        totalBase = itens.reduce((s, i) => s + (i.qtd * i.preco), 0);
        $('#valor-base-caixa').text('R$ ' + formatBR(totalBase));
        $('#valor-final-caixa').text('R$ ' + formatBR(totalBase));
        $('#campo_desconto').val('0,00');
        $('#tipo_desconto').val('valor');
        $('#operacao').val(operacao);
        $('#modalDesconto').modal('show');
    }
    $('#modalDesconto').on('shown.bs.modal', function () {$('#valor-base-caixa').text('R$ ' + formatBR(totalBase));});
    $('#campo_desconto, #tipo_desconto').on('input keyup change', function () {
        let tipo = $('#tipo_desconto').val();
        let valor = parseBR($('#campo_desconto').val());
        let final = totalBase;
        if (tipo === 'percentual') {valor = (valor / 100) * totalBase;}
        if ($('#operacao').val() === 'desconto') {final -= valor;}
        else {final += valor;}
        $('#valor-final-caixa').text('R$ ' + formatBR(final));
    });
    $('#confirmarDesconto').click(function () {
        iniciarLoading();
        descontoGeral.tipo = $('#tipo_desconto').val();
        descontoGeral.valor = parseBR($('#campo_desconto').val());
        descontoGeral.operacao = $('#operacao').val();
        aplicarDescontoGeral();
        renderItens();
        $('#modalDesconto').modal('hide');
        setTimeout(() => {
            $('.fecharmdDados').click();
        }, 300);
        fecharLoading();
    });
    function aplicarDescontoGeral() {
        if (!descontoGeral.tipo || descontoGeral.valor <= 0) {
            // 🔥 limpa ajustes
            itens.forEach(i => {
                i.total = i.qtd * i.preco;
                i.ajuste = 0;
                i.tipo_ajuste = null;
            });
            return;
        }
        let totalBase = itens.reduce((s, i) => s + (i.qtd * i.preco), 0);
        itens.forEach(item => {
            let base = item.qtd * item.preco;
            let ajuste = 0;
            if (descontoGeral.tipo === 'percentual') {ajuste = base * (descontoGeral.valor / 100);}
            else {
                let proporcao = base / totalBase;
                ajuste = descontoGeral.valor * proporcao;
            }
            if (descontoGeral.operacao === 'desconto') {
                item.total = base - ajuste;
                item.ajuste = -ajuste;
            } else {
                item.total = base + ajuste;
                item.ajuste = ajuste;
            }
            item.tipo_ajuste = descontoGeral.operacao;
        });
    }
    function setSelect2Value($select, id, text) {
        if (!id) return;
        // se opção não existe, cria
        if ($select.find(`option[value="${id}"]`).length === 0) {
            const option = new Option(text || id, id, true, true);
            $select.append(option);
        }
        $select.val(id).trigger('change');
    }
    $('#mdDadosVenda').on('show.bs.modal', function () {
        setSelect2Value($('#dadosCliente'), cliente?.id, cliente?.nome);
        setSelect2Value($('#dadosVendedor'), vendedor?.id, vendedor?.nome);
        setSelect2Value($('#dadosTabelaPrecos'), tabelaPreco?.id, tabelaPreco?.nome);
    });
    $('.alt_dadosVenda').click(function () {
        iniciarLoading();
        const dadoCli = $("#dadosCliente").val();
        const dadoVend = $("#dadosVendedor").val();
        const dadoTbPrec = $("#dadosTabelaPrecos").val();
        const tabelaAntiga = tabelaPreco?.id; // 🔥 guarda antes
        if (dadoCli) {cliente = {id: dadoCli, nome: $("#dadosCliente option:selected").text()};}
        if (dadoVend) {vendedor = {id: dadoVend, nome: $("#dadosVendedor option:selected").text()};}
        if (dadoTbPrec) {tabelaPreco = {id: dadoTbPrec, nome: $("#dadosTabelaPrecos option:selected").text()};}
        // 🔥 AGORA FUNCIONA
        if (dadoTbPrec && dadoTbPrec != tabelaAntiga) {atualizarPrecosItens();}
        toast(`Dados da venda atualizados!`, "success");
        $('#mdDadosVenda').modal('hide');
        atualizarResumoVenda();
        fecharLoading();
    });
    function atualizarResumoVenda() {
        $('#infoCliente').text(`Cliente: ${cliente?.nome || '-'}`);
        $('#infoVendedor').text(`Vendedor: ${vendedor?.nome || '-'}`);
        $('#infoTabelaPreco').text(`Tb. Preço: ${tabelaPreco?.nome || '-'}`);
    }
    function atualizarPrecosItens() {
        if (!tabelaPreco || itens.length === 0) return;
        iniciarLoading();
        fetch('/produtos/precos-lote/', {method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
            body: JSON.stringify({tabela_id: tabelaPreco.id, produtos: itens.map(i => String(i.produto_id))})
        }).then(r => r.json()).then(resp => {
            itens.forEach(item => {
                const novoPreco = resp.precos[String(item.produto_id)]; // 🔥 garante string
                if (novoPreco !== undefined) {item.preco = novoPreco;}
                else {item.preco = 0;}
                item.total = item.qtd * item.preco;
            });
            renderItens();
            toast(`Preços atualizados pela tabela`, "success");
            fecharLoading();
        });
    }
    /* RENDER */
    function renderItens() {
        let html = '';
        let total = 0;
        if (itens.length === 0) {
            html = `
                <div class="col-12 fw-bold text-center text-success descricao-col"><h1 style="text-align: center; margin-top: 20px; font-size: 6rem;"><strong>CAIXA LIVRE</strong></h1></div>
            `;
        } else {
            itens.forEach((i, index) => {
                total += i.total;
                html += `
                    <div class="list-group-item py-1 item-lista">
                        <div class="row align-items-center linha-lista">
                            <div class="col-md-1 fw-bold codigo-col">${index + 1}</div>
                            <div class="col-md-2 fw-bold codigo-col">${i.produto_id}</div>
                            <div class="col-md-3 fw-bold descricao-col">${i.desc}</div>
                            <div class="col-md-1 fw-bold codigo-col" style="font-size: 0.91rem;">${formatBR(i.preco)}</div>
                            <div class="col-md-1 fw-bold codigo-col">${formatBR(i.qtd)}</div>
                            <div class="col-md-2 fw-bold codigo-col">
                                ${formatBR(i.total)}
                                ${i.ajuste ? `<br>
                                    <small style="color:${i.ajuste < 0 ? 'error' : 'success'}">(${i.ajuste < 0 ? '-' : '+'} ${formatBR(Math.abs(i.ajuste))})</small>` : ''}
                            </div>
                            <div class="col-sm-2 fw-bold acoes-col">
                                <button class="editarItem btn btn-light border" data-index="${index}"><i class="fa-solid fa-pen-to-square text-success"></i></button>
                                <button class="btn-remover btn btn-light border" data-index="${index}"><i class="fa-solid fa-trash text-danger"></i></button>
                            </div>
                        </div>
                    </div>
                `;
            });
        }
        // Quando essa linha rodar, o jQuery vai ler a string inteira (incluindo as tags <i> do backend) e renderizar como HTML real
        $('.tb-cx-lista').html(html);
        $('#totalVenda').text(formatBR(total));
        $('#totalVendaBox').text(formatBR(total));
        $('.inp-valor-pgto').val(formatInputBR(total));
    }
    renderItens();
    /* REMOVER */
    $(document).on('click', '.btn-remover', function () {
        iniciarLoading();
        let index = $(this).data('index');
        itens.splice(index, 1);
        aplicarDescontoGeral();
        renderItens();
        fecharLoading();
    });
    /*EDITAR*/
    $(document).on('click', '.editarItem', async function () {
        editIndex = $(this).data('index');
        let item = itens[editIndex];
        // 🔥 PREENCHE CÓDIGO PRIMEIRO
        $('#id_cod_produtoEd').val(item.produto_id).prop('disabled', true);
        try {
            // 🔥 AGORA PASSA O CÓDIGO CORRETO
            const dados = await buscarDadosProduto(item.produto_id);
            $("#id_unidProdutoEd").val(dados.unidProd || "");
            $("#id_marcaProdEd").val(dados.marca || "");
            $("#id_grupoProdEd").val(dados.grupo || "");
        }
        catch (e) {console.warn('Erro ao buscar dados do produto:', e);}
        // 🔥 OUTROS CAMPOS
        $('#id_preco_unitEd').prop('disabled', true);
        $('#id_desc_prodEd').val(item.desc);
        $('#id_quantidadeEd').val(formatBR(item.qtd));
        $('#id_preco_unitEd').val(formatBR(item.preco));
        $('#id_desc_acresEd').val(formatBR(Math.abs(item.ajuste || 0)));
        $('#id_tipo_desc_acresEd').val(descontoGeral.tipo === 'percentual' ? 'Percentual' : 'Valor');
        if (item.ajuste < 0) {$('#lblDescAcres').text('Desconto');}
        else if (item.ajuste > 0) {$('#lblDescAcres').text('Acréscimo');}
        else {$('#lblDescAcres').text('Ajuste');}
        $('#edProdModalItem').modal('show');
    });
    /* SALVAR EDIÇÃO */
    $('#add-produto-listaItem').click(function () {
        if (editIndex === null) return;
        let qtd = parseBR($('#id_quantidadeEd').val());
        let preco = parseBR($('#id_preco_unitEd').val());
        if (qtd <= 0) {
            toast(`Quantidade inválida!`, "warning");
            return;
        }
        // 🔥 atualiza item
        itens[editIndex].qtd = qtd;
        itens[editIndex].preco = preco;
        // 🔥 recalcula total base
        itens[editIndex].total = qtd * preco;
        // 🔥 reaplica desconto/acréscimo geral se existir
        aplicarDescontoGeral();
        // 🔥 rerenderiza tabela
        renderItens();
        // 🔥 fecha modal
        $('#edProdModalItem').modal('hide');
        // 🔥 limpa índice
        toast(`Item ${editIndex + 1} atualizado!`, "success");
        editIndex = null;
    });
    /* LIMPAR CAMPOS AO FECHAR MODAL */
    $('#edProdModalItem').on('hidden.bs.modal', function () {
        editIndex = null;
        $('#id_cod_produtoCaixa').prop('disabled', false).val('');
        $('#id_desc_prodCaixa').val('');
        $('#id_quantidadeCaixa').val('1,00');
        $('#id_preco_unitCaixa').val('0,00');
    });
    /* LIMPAR */
    function limparCampos(){
        iniciarLoading();
        $('#id_cod_produtoCaixa').val('').focus();
        $('#id_desc_prodCaixa').val('');
        $('#id_quantidadeCaixa').val('1,00');
        fecharLoading();
    }
    /* CANCELAR */
    function cancelarVenda(){
        iniciarLoading();
        itens = [];
        renderItens();
        restaurarPadraoFilial();
        fecharLoading();
    }
    $("#finalizarVendaBtn").click(function () {
        if (itens.length === 0) {
            toast(`Adicione ao menos um item para finalizar a venda!`, "warning");
            return;
        }
        iniciarLoading();
        const $modal = $('.modal-pagamento');
        // 🔥 TOTAL DA VENDA
        const total = itens.reduce((s, i) => s + i.total, 0);
        // 🔥 CLIENTE
        $modal.find('.vendaCliente').val(cliente?.nome);
        // 🔥 TOTAL NO CAMPO
        $modal.find('.totalModal').val(formatBR(total));
        // 🔥 JOGA NO INPUT DA FORMA (FORMATO INPUT)
        $modal.find('.inp-valor-pgto').val(formatInputBR(total));
        // 🔥 (OPCIONAL) LIMPA E SETA SELECT2
        const $select = $modal.find('.forma-pgto');
        // limpa seleção
        $select.val(null).trigger('change');
        // se quiser já deixar DINHEIRO (exemplo id = 1)
        const defaultFormaId = $select.find('option:first').val();
        if (defaultFormaId) {
            $select.val(defaultFormaId).trigger('change');
        }
        // 🔥 abre modal
        $modal.modal('show');
        fecharLoading();
    });
    $("#cancelarVendaBtn").click(function(){
        cancelarVenda();
        // 🔥 ZERA DESCONTO / ACRÉSCIMO
        descontoGeral = {tipo: 'valor', valor: 0, operacao: null};
        $("#id_preco_unitCaixa").val('0,00');
        $("#id_cod_produtoCaixa").val('').focus();
        renderItens();
    });
    function formatDataHora(dataStr) {
        if (!dataStr) return '-';
        const data = new Date(dataStr);
        if (isNaN(data)) return '-';
        return data.toLocaleString('pt-BR', {day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit'});
    }
    $("#formEntrada").submit(function(e){
        e.preventDefault();
        let desc = $("#desc_entrada").val();
        const selectData = $('#forma_entrada').select2('data');
        const formaPgto  = selectData[0]?.id;
        const valor    = parseBR($('#vl_entrada').val());
        if (!desc) {
            toast("Descrição deve ser informada!", "warning");
            return;
        }
        if (!formaPgto) {
            toast("Forma de pagamento deve ser informada!", "warning");
            return;
        }
        if (!valor || valor <= 0) {
            toast("Valor deve ser informado!", "warning");
            return;
        }
        $.ajax({
            url: $(this).attr("action"), type: "POST", data: $(this).serialize(), success: function(data){
                if(data.sucesso){
                    $("#modalEntrada").modal("hide");
                    imprimirComprovanteEntrada(data);
                    $('#forma_entrada').val(null).trigger('change');
                    $("#vl_entrada, #desc_entrada").val("");
                    toast(`Entrada registrada com sucesso!`, "success");
                }
            },
            error: function(xhr){toast(xhr.responseJSON.erro, 'error');}
        });
    });
    function imprimirComprovanteEntrada(dados){
        let frame = document.getElementById("frameImpressao");
        let doc = frame.contentWindow.document;
        doc.open();
        doc.write(`
            <style>
                @page {margin: 0;}
                body {margin: 0; padding: 0;}
                #cupom {width: 100%; max-width: 72mm; font-family: monospace; font-size: 10px; margin: 0; padding: 5px; border: 1px dashed #000;}
                .center {text-align: center;}
                .bold {font-weight: bold;}
                .linha {border-top: 1px dashed #000; margin: 3px 0;}
                .flex {display: flex; justify-content: space-between;}
                .small {font-size: 11px;}
                img {max-width: 120px; margin: 0 auto; display: block;}
                .assinaturas {display: flex; justify-content: space-between; margin-top: 40px;}
                .assinatura {width: 45%; text-align: center;}
                .assinatura .linha-ass {border-top: 1px solid #000; margin-bottom: 4px;}
            </style>
            <div id="cupom" class="bold">
                <div class="center small">
                    <div>${dados.fantasia}</div>
                    <div>${dados.endereco}, ${dados.numero}</div>
                    <div>${dados.bairro} - ${dados.cidade} - ${dados.uf}</div>
                    <div>${dados.tel}</div>
                </div>
                <div class="linha"></div>
                <div class="center small">ENTRADA NO CAIXA</div>
                <div class="linha"></div>
                <div class="small">
                    <div>CAIXA: ${dados.caixa}</div>
                    <div>Nº DOC.: ${dados.cod_cx}/${dados.id}</div>
                    <div>DESCRIÇÃO: ${dados.descricao}</div>
                    <div>DT-HR: ${dados.data}</div>
                </div>
                <div class="linha"></div>
                <div class="small">
                    <div>${dados.forma} <span style="float: right;">R$ ${formatBR(dados.valor)}</span></div>
                </div>
                <div class="assinaturas">
                    <div class="assinatura">
                        <div class="linha-ass"></div>
                        <div>CAIXA</div>
                    </div>
                    <div class="assinatura">
                        <div class="linha-ass"></div>
                        <div>RESPONSÁVEL</div>
                    </div>
                </div>
            </div>
        `);
        doc.close();
        frame.contentWindow.focus();
        frame.contentWindow.print();
    }
    $("#formSaida").submit(function(e){
        e.preventDefault();
        let desc = $("#desc_saida").val();
        const selectData = $('#forma_saida').select2('data');
        const formaPgto  = selectData[0]?.id;
        const valor    = parseBR($('#vl_saida').val());
        if (!desc) {
            toast("Descrição deve ser informada!", "warning");
            return;
        }
        if (!formaPgto) {
            toast("Forma de pagamento deve ser informada!", "warning");
            return;
        }
        if (!valor || valor <= 0) {
            toast("Valor deve ser informado!", "warning");
            return;
        }
        $.ajax({
            url: $(this).attr("action"), type: "POST", data: $(this).serialize(), success: function(data){
                if(data.sucesso){
                    $("#modalSaida").modal("hide");
                    imprimirComprovanteSaida(data);
                    $('#forma_saida').val(null).trigger('change');
                    $("#vl_saida, #desc_saida").val("");
                    toast(`Saída registrada com sucesso!`, "success");
                }
            },
            error: function(xhr){toast(xhr.responseJSON.erro, 'error');}
        });
    });
    function imprimirComprovanteSaida(dados){
        let frame = document.getElementById("frameImpressaoSaida");
        let doc = frame.contentWindow.document;
        doc.open();
        doc.write(`
            <style>
                @page {margin: 0;}
                body {margin: 0; padding: 0;}
                #cupom {width: 100%; max-width: 72mm; font-family: monospace; font-size: 10px; margin: 0; padding: 5px; border: 1px dashed #000;}
                .center {text-align: center;}
                .bold {font-weight: bold;}
                .linha {border-top: 1px dashed #000; margin: 3px 0;}
                .flex {display: flex; justify-content: space-between;}
                .small {font-size: 11px;}
                img {max-width: 120px; margin: 0 auto; display: block;}
                .assinaturas {display: flex; justify-content: space-between; margin-top: 40px;}
                .assinatura {width: 45%; text-align: center;}
                .assinatura .linha-ass {border-top: 1px solid #000; margin-bottom: 4px;}
            </style>
            <div id="cupom" class="bold">
                <div class="center small">
                    <div>${dados.fantasia}</div>
                    <div>${dados.endereco}, ${dados.numero}</div>
                    <div>${dados.bairro} - ${dados.cidade} - ${dados.uf}</div>
                    <div>${dados.tel}</div>
                </div>
                <div class="linha"></div>
                <div class="center small">SAÍDA DO CAIXA</div>
                <div class="linha"></div>
                <div class="small">
                    <div>CAIXA: ${dados.caixa}</div>
                    <div>Nº DOC.: ${dados.cod_cx}/${dados.id}</div>
                    <div>DESCRIÇÃO: ${dados.descricao}</div>
                    <div>DT-HR: ${dados.data}</div>
                </div>
                <div class="linha"></div>
                <div class="small">
                    <div>${dados.forma} <span style="float: right;">R$ ${formatBR(dados.valor)}</span></div>
                </div>
                <div class="assinaturas">
                    <div class="assinatura">
                        <div class="linha-ass"></div>
                        <div>CAIXA</div>
                    </div>
                    <div class="assinatura">
                        <div class="linha-ass"></div>
                        <div>RESPONSÁVEL</div>
                    </div>
                </div>
            </div>
        `);
        doc.close();
        frame.contentWindow.focus();
        frame.contentWindow.print();
    }
    function abrirMovCaixa(caixaId) {
        iniciarLoading();
        fetch(`/lancpdvs/caixa/movimentos/${caixaId}/`).then(r => r.json()).then(resp => {
            if (resp.erro) {
                toast(`${resp.erro}`, "error");
                return;
            }
            $('#tblAbertura, #tblVendas, #tblResumoVendas, #tblEntradas, #tblResumoEntradas, #tblSaidas, #tblResumoSaidas, #tblTotalGeral, #totVendasCaixa').html('');
            // 🔹 ABERTURA
            resp.abertura.forEach(a => {
                $('#tblAbertura').append(`
                    <tr>
                        <td>${formatDataHora(a.data)}</td><td>${a.descricao}</td><td>${a.forma}</td><td class="text-end">${formatBR(a.valor)}</td>
                    </tr>
                `);
            });
            // 🔹 VENDAS
            resp.vendas.forEach(v => {
                let formasHtml = '';
                v.formas.forEach(f => {
                    formasHtml += `
                        <div class="p-1 mb-1 bg-secondary text-light rounded-3" style="font-size: 0.8rem;">
                            ${f.forma} <span style="float:right;">${formatBR(f.valor)}</span>
                        </div>
                    `;
                });
                let cor = "";
                if (v.situacao === "Faturado") {cor = "badge text-bg-success";}
                else {cor = "badge text-bg-danger";}
                // 🔥 ícone condicional
                const iconeDevolucao = v.tem_devolucao ? `<i class="fa-solid fa-arrows-rotate text-primary-emphasis fa-spin me-1" title="Pedido com itens devolvidos."></i> ` : '';
                $('#tblVendas').append(`
                    <tr>
                        <td>${iconeDevolucao}${v.pedido_id}</td><td>${v.cliente}</td><td>${v.vendedor}</td><td>${formatDataHora(v.data)}</td>
                        <td class="text-center"><span class="${cor}">${v.situacao}</span></td>
                        <td><div style=" font-weight: bold; max-height:3.5em; overflow-y:auto; white-space:normal; line-height:0.6em;">${formasHtml}</div></td>
                        <td class="text-end fw-bold">${formatBR(v.total)}</td>
                        <td class="text-center">
                            <a href="/pedidos/cupom/${v.pedido_id}/" target="_blank">
                            <button class="btn btn-dark btn-sm"><i class="fa-solid fa-receipt text-white fs-5"></i></button>
                            </a>
                        </td>
                    </tr>
                `);
            });
            $('#totVendasCaixa').append(`
                <div class="row">
                    <div class="card-body col-md-6 fw-bold text-dark text-start" style="margin: -10px;">Quantidade de Vendas: <span class="badge text-bg-success">${resp.vendas.length}</span></div>
                    <div class="card-body col-md-6 fw-bold text-dark text-end" style="margin: -10px;">Valor Total: <span class="badge text-bg-success">R$ ${formatBR(resp.total_vendas)}</span></div>
                </div>
            `);
            // 🔹 RESUMO VENDAS
            resp.resumo_vendas.forEach(r => {
                $('#tblResumoVendas').append(`
                    <tr>
                        <td>${r.id}</td><td>${r.forma}</td><td class="text-end">${formatBR(r.total)}</td>
                    </tr>
                `);
            });
            // 🔹 ENTRADAS
            resp.entradas.forEach(e => {
                let disabled = "";
                if (e.situacao === "Cancelado") {
                    disabled = "disabled";
                    $('#tblEntradas').append(`
                        <tr>
                            <td>${e.codigo}</td><td>${e.descricao}</td><td>${e.forma}</td><td class="text-end">${formatBR(e.valor)}</td>
                            <td class="col-auto" style="text-align: center;">
                                <button class="btn btn-danger btn-sm btnCancelarEntrada" data-caixa="${resp.caixa}" data-movimento="${e.codigo}" ${disabled} title="Entrada já cancelada!">
                                    <i class="fa-solid fa-ban text-white fs-5"></i>
                                </button>
                                <button class="btn btn-primary btn-sm btnReimprimirEntrada" data-caixa="${resp.caixa}" data-movimento="${e.codigo}">
                                    <i class="fa-solid fa-receipt text-white fs-5"></i>
                                </button>
                            </td>
                        </tr>
                    `);
                } else {
                    $('#tblEntradas').append(`
                        <tr>
                            <td>${e.codigo}</td><td>${e.descricao}</td><td>${e.forma}</td>
                            <td class="text-end">${formatBR(e.valor)}</td>
                            <td class="col-auto" style="text-align: center;">
                                <button class="btn btn-danger btn-sm btnCancelarEntrada" data-caixa="${resp.caixa}" data-movimento="${e.codigo}" title="Cancelar Entrada!">
                                    <i class="fa-solid fa-ban text-white fs-5"></i>
                                </button>
                                <button class="btn btn-primary btn-sm btnReimprimirEntrada" data-caixa="${resp.caixa}" data-movimento="${e.codigo}">
                                    <i class="fa-solid fa-receipt text-white fs-5"></i>
                                </button>
                            </td>
                        </tr>
                    `);
                }
            });
            // 🔹 RESUMO ENTRADAS
            resp.resumo_entradas.forEach(r => {
                $('#tblResumoEntradas').append(`
                    <tr>
                        <td>${r.forma}</td><td class="text-end">${formatBR(r.total)}</td>
                    </tr>
                `);
            });
            // 🔹 SAÍDAS
            resp.saidas.forEach(sai => {
                let disabled = "";
                if (sai.situacao === "Cancelado") {
                    disabled = "disabled";
                    $('#tblSaidas').append(`
                        <tr>
                            <td>${sai.codigo}</td>
                            <td>${sai.descricao}</td>
                            <td>${sai.forma}</td>
                            <td class="text-end text-danger">${formatBR(sai.valor)}</td>
                            <td class="col-auto" style="text-align: center;">
                                <button class="btn btn-danger btn-sm btnCancelarSaida" data-caixa="${resp.caixa}" data-movimento="${sai.codigo}" ${disabled} title="Saída já cancelada!">
                                    <i class="fa-solid fa-ban text-white fs-5"></i>
                                </button>
                                <button class="btn btn-primary btn-sm btnReimprimirSaida" data-caixa="${resp.caixa}" data-movimento="${sai.codigo}">
                                    <i class="fa-solid fa-receipt text-white fs-5"></i>
                                </button>
                            </td>
                        </tr>
                    `);
                } else {
                    $('#tblSaidas').append(`
                        <tr>
                            <td>${sai.codigo}</td>
                            <td>${sai.descricao}</td>
                            <td>${sai.forma}</td>
                            <td class="text-end text-danger">${formatBR(sai.valor)}</td>
                            <td class="col-auto" style="text-align: center;">
                                <button class="btn btn-danger btn-sm btnCancelarSaida" data-caixa="${resp.caixa}" data-movimento="${sai.codigo}" title="Cancelar Saída!">
                                    <i class="fa-solid fa-ban text-white fs-5"></i>
                                </button>
                                <button class="btn btn-primary btn-sm btnReimprimirSaida" data-caixa="${resp.caixa}" data-movimento="${sai.codigo}">
                                    <i class="fa-solid fa-receipt text-white fs-5"></i>
                                </button>
                            </td>
                        </tr>
                    `);
                }
            });
            // 🔹 RESUMO SAÍDAS
            resp.resumo_saidas.forEach(res => {
                $('#tblResumoSaidas').append(`
                    <tr>
                        <td>${res.forma}</td><td class="text-end text-danger">${formatBR(res.total)}</td>
                    </tr>
                `);
            });
            // 🔹 TOTAL GERAL
            resp.total_geral.forEach(t => {
                $('#tblTotalGeral').append(`
                    <tr>
                        <th>${t.forma}</th><th class="text-end">${formatBR(t.total)}</th>
                    </tr>
                `);
            });
        });
        fecharLoading();
    }
    $(document).on("click", ".btnReimprimirEntrada", function () {
        const caixa = $(this).data("caixa");
        const movimento = $(this).data("movimento");
        $.get(`/lancpdvs/caixa/${caixa}/movimento/${movimento}/`, function (data) {
            if (data.sucesso) {imprimirComprovanteEntrada(data);}
            else {toast(data.erro, "error");}
        });
    });
    $(document).on("click", ".btnReimprimirSaida", function () {
        const caixa = $(this).data("caixa");
        const movimento = $(this).data("movimento");
        $.get(`/lancpdvs/caixa/${caixa}/movimento/${movimento}/`, function (data) {
            if (data.sucesso) {imprimirComprovanteSaida(data);}
            else {toast(data.erro, "error");}
        });
    });
    $(document).on("click", ".btnCancelarEntrada, .btnCancelarSaida", function () {
        const botao = $(this);
        const caixa = botao.data("caixa");
        const movimento = botao.data("movimento");
        if (!confirm("Deseja realmente cancelar este lançamento?")) {return;}
        $.ajax({
            url: `/lancpdvs/caixa/${caixa}/movimento/${movimento}/cancelar/`, type: "POST", headers: {"X-CSRFToken": $("[name=csrfmiddlewaretoken]").val()},
            success: function (resp) {
                toast(resp.mensagem, "success");
                // Remove os botões de cancelar
                botao.closest("td").find(".btnCancelarEntrada, .btnCancelarSaida").remove();
                // Opcional: marca a linha como cancelada
                botao.closest("tr").addClass("table-danger");
                // Atualiza os totais do caixa
                abrirMovCaixa(caixa);
            },
            error: function (xhr) {
                let erro = "Erro ao cancelar lançamento.";
                if (xhr.responseJSON && xhr.responseJSON.erro) {erro = xhr.responseJSON.erro;}
                toast(erro, "error");
            }
        });
    });
    $(document).on('click', '.btnMovi', function () {
        const caixaId = $(this).data('caixa-id');
        if (!caixaId) {
            toast('ID do caixa não encontrado!', 'warning');
            return;
        }
        abrirMovCaixa(caixaId);
    });
    let codigoPedidoOrigemAtual = null;
    // 1. EVENTO DE BUSCA: Quando clica em "Consultar" no modal
    $('#btnBuscarPedidoTroca').on('click', function() {
        let codigoPedido = $('#inputCodigoPedido').val().trim();
        if (!codigoPedido) {
            toast("Código do Pedido é necessário!", "warning");
            return;
        }
        // Bloqueia o botão para evitar cliques duplos durante a requisição
        let $btn = $(this);
        $btn.prop('disabled', true).text('Buscando...');
        // Faz a chamada para a sua view existente 'buscar_pedido_troca_devolucao'
        $.ajax({
            url: '/lancpdvs/caixa/busca.pedido/', type: 'GET', data: {'codigo': codigoPedido}, dataType: 'json', success: function(response) {
                if (response.sucesso) {
                    codigoPedidoOrigemAtual = response.pedido.codigo;
                    // Preenche os metadados do pedido no card
                    $('#txtClienteOriginal').text(response.pedido.cliente);
                    $('#txtDataOriginal').text(response.pedido.data);
                    $('#txtTotalOriginal').text('R$ ' + formatBR(response.pedido.total));
                    // Limpa e reconstrói as linhas da tabela de itens
                    let $tbody = $('#tbodyItensPedidoOriginal');
                    $tbody.empty();
                    response.itens.forEach(function(item) {
                        let linha = `
                            <tr>
                                <td class="text-center"><input class="form-check-input chk-item-devolver" type="checkbox" data-item-id="${item.item_id}"></td>
                                <td>${item.codigo}</td><td>${item.descricao}</td><td class="text-center fw-bold text-secondary">${formatBR(item.quantidade_disponivel)}</td>
                                <td>
                                    <input type="number" class="form-control form-control-sm text-center input-qtd-devolver"  min="0.01" max="${item.quantidade_disponivel}" step="0.01" value="${parseBR(item.quantidade_disponivel)}" disabled>
                                </td>
                                <td class="text-end">R$ ${formatBR(item.valor_unitario)}</td>
                            </tr>
                        `;
                        $tbody.append(linha);
                    });
                    // Exibe as áreas ocultas do modal
                    $('#dadosPedidoOriginal').removeClass('d-none');
                    $('#containerItensTroca').removeClass('d-none');
                    $('#btnConfirmarItensModal').removeClass('d-none');
                } else {
                    toast(response.erro, "error");
                    resetarCamposModal();
                }
            },
            error: function(xhr, status, error) {
                toast(`Erro de comunicação com o servidor: ${error}`, "error");
                resetarCamposModal();
            },
            complete: function() {$btn.prop('disabled', false).text('Consultar');}
        });
    });
    // 2. CONTROLE INTERNO DO MODAL: Ativar/Desativar o input de quantidade ao marcar o Checkbox
    $(document).on('change', '.chk-item-devolver', function() {
        let $linha = $(this).closest('tr');
        let $inputQtd = $linha.find('.input-qtd-devolver');
        if ($(this).is(':checked')) {$inputQtd.prop('disabled', false).focus();}
        else {$inputQtd.prop('disabled', true);}
    });
    // 3. EVENTO DE CONFIRMAÇÃO: Quando clica em "Injetar no Carrinho"
    $('#btnConfirmarItensModal').on('click', function() {
        let itensSelecionados = [];
        // Varre apenas as linhas onde o checkbox foi marcado
        $('.chk-item-devolver:checked').each(function() {
            let $linha = $(this).closest('tr');
            let itemId = $(this).data('item-id'); // ID da linha PedidoProduto
            let quantidade = parseBR($linha.find('.input-qtd-devolver').val());
            if (quantidade > 0) {itensSelecionados.push({"item_id": itemId, "quantidade": quantidade});}
        });
        if (itensSelecionados.length === 0) {
            toast("Selecione ao menos um produto e defina a quantidade para devolução!", "warning");
            return;
        }
        let $btn = $(this);
        $btn.prop('disabled', true).text('Validando...');
        // Envia para a view de validação em segundo plano (evita fraudes/erros de digitação de estoque)
        $.ajax({
            url: '/lancpdvs/caixa/validar.itens.devolucao/', type: 'POST', contentType: 'application/json', headers: { 'X-CSRFToken': getCookie('csrftoken') },
            data: JSON.stringify({"codigo_pedido": codigoPedidoOrigemAtual, "itens": itensSelecionados}),
            success: function(response) {
                if (response.sucesso) {
                    // 🔥 Injeta os itens formatados negativamente no carrinho principal da tela do caixa
                    response.itens.forEach(function(item) {
                        // Função que você deve criar ou adaptar no seu script do caixa principal para adicionar itens no grid
                        adicionarItemAoCarrinhoCaixa(item);
                    });
                    // Guarda o código do pedido de origem em algum campo oculto ou variável global do seu formulário do caixa
                    // para ser enviado de volta quando a view 'finalizar_venda' for executada.
                    $('#id_input_codigo_pedido_origem_oculto').val(codigoPedidoOrigemAtual);
                    // Fecha o modal do Bootstrap de forma limpa
                    let modalElement = document.getElementById('modalTrocaDevolucao');
                    let modalInstance = bootstrap.Modal.getInstance(modalElement);
                    modalInstance.hide();
                    // Limpa o modal para uma próxima utilização
                    resetarCamposModal(true);
                }
                else {toast(`Erro na validação: ${response.erro}`, "error");}
            },
            error: function(xhr, status, error) {toast(`Erro ao validar itens: ${error}`, "error");},
            complete: function() {$btn.prop('disabled', false).html('<i class="fa-regular fa-circle-check"></i> Confirmar');}
        });
    });
    function resetarCamposModal(limparInputBusca = false) {
        if (limparInputBusca) {
            $('#inputCodigoPedido').val('');
            codigoPedidoOrigemAtual = null;
        }
        // Garante que o container e os botões sumam da tela se o pedido não tiver saldo
        $('#dadosPedidoOriginal').addClass('d-none');
        $('#containerItensTroca').addClass('d-none');
        $('#btnConfirmarItensModal').addClass('d-none').prop('disabled', false).html('<i class="fa-regular fa-circle-check"></i> Confirmar');
        $('#tbodyItensPedidoOriginal').empty();
    }
    // FECHAMENTO DE CAIXA
    let _dadosFechamento = [];
    function abrirModalFechamento() {
        iniciarLoading();
        let caixaId = CAIXA_ID;
        fetch(`/lancpdvs/caixa/dados-fechamento/${caixaId}/`).then(r => r.json()).then(resp => {
            if (!resp.sucesso) {
                toast(resp.erro || 'Erro ao carregar dados.', 'error');
                fecharLoading();
                return;
            }
            _dadosFechamento = resp.formas;
            const $lista = $('#listaFechamento').empty();
            resp.formas.forEach((f, idx) => {
                $lista.append(`
                    <div class="row g-0 align-items-center border-bottom py-2 linha-fechamento" data-idx="${idx}" style="transition: background .15s;">
                        <div class="col-4 ps-4 fw-semibold" style="font-size:0.9rem;">${f.descricao}</div>
                        <div class="col-4 text-center"><span class="text-muted fw-bold vl-sistema-fechamento">${formatBR(f.total)}</span></div>
                        <div class="col-4 d-flex justify-content-center pe-3">
                            <input type="text" class="form-control form-control-sm text-end fw-bold inp-fechamento" data-idx="${idx}" data-sistema="${f.total}" value="${formatBR(f.total)}" style="max-width: 130px;">
                        </div>
                    </div>
                `);
            });
            recalcularTotaisFechamento();
            fecharLoading();
            new bootstrap.Modal(document.getElementById('modalFechamentoCaixa')).show();
        }).catch(() => {
            toast('Erro de comunicação.', 'error');
            fecharLoading();
        });
    }
    $(".fechar-caixa").click(function(){
        iniciarLoading();
        abrirModalFechamento();
        fecharLoading();
    });
    function recalcularTotaisFechamento() {
        let totalSistema = 0;
        let totalInformado = 0;
        $('.inp-fechamento').each(function () {
            const sistema = parseBR($(this).data('sistema')) || 0;
            const informado = parseBR($(this).val()) || 0;
            totalSistema += sistema;
            totalInformado += informado;
            // destaca linha com diferença
            const linha = $(this).closest('.linha-fechamento');
            if (Math.abs(informado - sistema) > 0.009) {linha.css('background', '#fff8e1');}
            else {linha.css('background', '');}
        });
        const diferenca = totalInformado - totalSistema;
        $('#totalSistemaFechamento').text('R$ ' + formatBR(totalSistema));
        $('#totalInformadoFechamento').text('R$ ' + formatBR(totalInformado));
        const $dif = $('#diferencaFechamento');
        $dif.text((diferenca >= 0 ? '+ ' : '- ') + 'R$ ' + formatBR(Math.abs(diferenca)));
        $dif.css('color', diferenca < -0.009 ? '#dc3545' : diferenca > 0.009 ? '#198754' : '#6c757d');
    }
    // Recalcula ao digitar
    $(document).on('input', '.inp-fechamento', function () {
        aplicarMascaraMoney(this);
        recalcularTotaisFechamento();
    });
    $(document).on('blur', '.inp-fechamento', function () {
        const num = parseBR($(this).val()) || 0;
        $(this).val(formatBR(num));
        recalcularTotaisFechamento();
    });
    // Confirmar fechamento
    $('#btnConfirmarFechamento').on('click', function () {
        const fechamentos = [];
        $('.inp-fechamento').each(function (i) {
            const f = _dadosFechamento[i];
            fechamentos.push({forma_codigo: f.forma_id, valor_sistema: f.total, valor_informado: parseBR($(this).val()) || 0,});
        });
        iniciarLoading();
        console.log(fechamentos);
        fetch(`/lancpdvs/caixa/fechar/${CAIXA_ID}/`, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
            body: JSON.stringify({ fechamentos })
        }).then(r => r.json()).then(resp => {
            if (resp.sucesso) {
                toast(resp.mensagem, 'success');
                bootstrap.Modal.getInstance(document.getElementById('modalFechamentoCaixa')).hide();
                setTimeout(() => window.location.href = `/lancpdvs/lista/?s=${CAIXA_ID}`, 3000);
            }
            else {
                toast(resp.erro || 'Erro ao fechar caixa.', 'error');
                fecharLoading();
                return;
            }
        }).catch(() => {
            fecharLoading();
            toast('Erro de comunicação.', 'error');
        });
    });
    // Configuração dos tipos de toast
    const TOASTS = {
        success: {cor: "linear-gradient(to right, #00b09b, #96c93d)", icone: "<i class='fa-solid fa-circle-check'></i>"},
        error: {cor: "linear-gradient(to right, #ff416c, #ff4b2b)", icone: "<i class='fa-solid fa-circle-xmark text-white'></i>"},
        warning: {cor: "linear-gradient(to right, #ff9f00, #ff6f00)", icone: "<i class='fa-solid fa-triangle-exclamation'></i>"},
        info: {cor: "linear-gradient(to right, #02202B, #017AB1)", icone: "<i class='fa-solid fa-circle-exclamation'></i>"},
        default: {cor: "linear-gradient(to right, #333, #555)", icone: "<i class='fa-solid fa-hourglass-end'></i>"}
    };
    function toast(texto, tipo = "default") {
        const toastCfg = TOASTS[tipo] || TOASTS.default;
        Toastify({text: `<span style="display:flex;align-items:center;gap:8px;">${toastCfg.icone} ${texto}</span>`, duration: 5000, gravity: "top",
            position: "center", style: {background: toastCfg.cor}, stopOnFocus: true, escapeMarkup: false,
            onClick() {
                document.querySelectorAll(".toastify").forEach(el => {
                    el.style.transition = "opacity .5s";
                    el.style.opacity = "0";
                    setTimeout(() => el.remove(), 500);
                });
            }
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
    function verificarPortaoSocial() {
        iniciarLoading();
        const p_social = $('#id_portao_social').val();
        if (p_social === 'Não') {
            $("#id_vl_p_s").val('0,00');
            $("#id_vl_p_s").prop("readonly", true).addClass("d-none");
            $("#id_lg_ps").prop("readonly", true).addClass("d-none");
            $("#id_at_ps").prop("readonly", true).addClass("d-none");
            $("#div_id_vl_p_s").addClass("d-none");
            $("#div_id_lg_ps").addClass("d-none");
            $("#div_id_at_ps").addClass("d-none");
            atualizarSubtotal();
        } else if (p_social === 'Sim') {
            $("#id_vl_p_s").prop("readonly", false).removeClass("d-none");
            $("#id_lg_ps").prop("readonly", false).removeClass("d-none");
            $("#id_at_ps").prop("readonly", false).removeClass("d-none");
            $("#div_id_vl_p_s").removeClass("d-none");
            $("#div_id_lg_ps").removeClass("d-none");
            $("#div_id_at_ps").removeClass("d-none");
        }
        fecharLoading();
    }
    verificarPortaoSocial();
    // Ao alterar o campo
    $('#id_portao_social').on('change', function () {verificarPortaoSocial();});
    function verificarOpEixo() {
        const p_e = $('#id_especifico').val();
        if (p_e === 'Eixo') {$("#div_id_diametro_eixo").removeClass("d-none");}
        else {$("#div_id_diametro_eixo").addClass("d-none");}
    }
    verificarOpEixo();
    function verificarOpLam() {
        const p_e = $('#id_especifico').val();
        if (p_e === 'Lâmina') {$("#div_id_espessura_lam, #div_id_peso_m2").removeClass("d-none");}
        else {$("#div_id_espessura_lam, #div_id_peso_m2").addClass("d-none");}
    }
    verificarOpLam();
    $("#id_vl_p_s").on("blur", function() {
        iniciarLoading();
        atualizarSubtotal();
        fecharLoading();
    });
    // Ao alterar o campo
    $('#id_especifico').on('change', function () {
        verificarOpEixo();
        verificarOpLam();
    });
    function verificarGateway() {
        const p_e = $('#id_gateway').val();
        if (p_e != 'nenhum') {$("#div_id_ambiente").removeClass("d-none");}
        else {$("#div_id_ambiente").addClass("d-none");}
    }
    verificarGateway();
    $('#id_gateway').on('change', function () {
        verificarGateway();
    });
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
                toast(`Status atualizado com sucesso!`, "success");
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
            error: function () {toast(`Erro ao atualizar o status!`, "error");}
        });
    });
    $(function () {$('[data-bs-toggle="tooltip"]').each(function () {new bootstrap.Tooltip(this);});});
    $(function () {
        function iniciarSelect2(ctx) {
            ctx = ctx || document;
            $(ctx).find('.produto-select').each(function () {
                if ($(this).hasClass("select2-hidden-accessible")) return;

                var $sel = $(this);
                var $selected = $sel.find('option[value!=""]:selected');
                var valorAtual = $selected.val() || '';
                var textoAtual = $selected.text() || '';

                $sel.select2({
                    placeholder: opSel,
                    allowClear: true,
                    minimumInputLength: 1,
                    templateResult: rendOpt,
                    templateSelection: d => d.text,
                    language: lingSel,
                    ajax: ajSel2('/produtos/lista_ajax1/')
                }).on('select2:open', focSel2);

                if (valorAtual) {
                    // Remove duplicatas que o trigger anterior pode ter criado
                    $sel.find('option[value="' + valorAtual + '"]').not(':last').remove();
                    $sel.val(valorAtual).trigger('change.select2');
                }
            });
        }
        // Inicializa ao carregar — passa o tbody para pegar todas as linhas existentes
        const OPERADORES = ['=', '>', '<', '>=', '<=', 'IN'];
        const OPERADORES_LABEL = {'=': 'Igual', '>': 'Maior', '<': 'Menor', '>=': 'Maior ou igual', '<=': 'Menor ou igual', 'IN': 'Está entre'};
        // Monta select de operadores
        function selectOperador(valor) {
            let html = '<select class="form-select form-select-sm cond-op">';
            OPERADORES.forEach(op => {
                const sel = op === valor ? 'selected' : '';
                html += `<option value="${op}" ${sel}>${OPERADORES_LABEL[op]}</option>`;
            });
            html += '</select>';
            return html;
        }
        // Monta linha de condição
        function novaLinhaCond(campo='', op='<=', valor='', ordem=0) {
            return `
                <tr class="cond-row">
                    <td><input type="text" class="form-control form-control-sm cond-campo" value="${campo}" placeholder="Ex: peso"></td>
                    <td>${selectOperador(op)}</td>
                    <td><input type="text" class="form-control form-control-sm cond-valor" value="${valor}" placeholder="Ex: 300"></td>
                    <td><input type="number" class="form-control form-control-sm cond-ordem" value="${ordem}" min="0" style="width:70px"></td>
                    <td><button type="button" class="btn btn-light border btn-sm remover-cond"><i class="fas fa-trash"></i></button></td>
                </tr>`;
        }
        // Lê condições de um item e atualiza o campo hidden JSON
        function atualizarCondJson($itemRow) {
            const $condRow = $itemRow.next('.condicoes-row');
            const condicoes = [];
            $condRow.find('.cond-row').each(function () {
                condicoes.push({campo: $(this).find('.cond-campo').val().trim(), operador: $(this).find('.cond-op').val(),
                    valor: $(this).find('.cond-valor').val().trim(), ordem: parseInt($(this).find('.cond-ordem').val()) || 0,
                });
            });
            $itemRow.find('input[name$="-condicoes_json"]').val(JSON.stringify(condicoes));
        }
        // Carrega condições existentes na sub-tabela ao abrir
        function carregarCondicoes($itemRow) {
            const $condRow = $itemRow.next('.condicoes-row');
            const $tbody = $condRow.find('.cond-tbody');
            if ($tbody.data('carregado')) return;

            $tbody.empty();

            const raw = $itemRow.find('input[name$="-condicoes_json"]').val();
            if (raw) {
                try {
                    const condicoes = JSON.parse(raw);
                    condicoes
                        // Filtra linhas completamente vazias
                        .filter(c => c.campo && c.campo.trim() !== '')
                        .forEach(c => {
                            $tbody.append(novaLinhaCond(c.campo, c.operador, c.valor, c.ordem));
                        });
                } catch(e) {}
            }
            $tbody.data('carregado', true);
        }
        // Toggle sub-tabela de condições
        $(document).on('click', '.btn-condicoes', function () {
            const $itemRow = $(this).closest('.item-row');
            const $condRow = $itemRow.next('.condicoes-row');
            carregarCondicoes($itemRow);
            $condRow.toggle();
        });
        // Adicionar condição
        $(document).on('click', '.btn-add-cond', function () {
            const $tbody = $(this).closest('td').find('.cond-tbody');
            const ordem = $tbody.find('.cond-row').length + 1;
            $tbody.append(novaLinhaCond('', '<=', '', ordem));
        });
        // Remover condição
        $(document).on('click', '.remover-cond', function () {
            const $itemRow = $(this).closest('.condicoes-row').prev('.item-row');
            $(this).closest('.cond-row').remove();
            atualizarCondJson($itemRow);
        });
        // Atualiza JSON ao mudar qualquer campo de condição
        $(document).on('input change', '.cond-campo, .cond-op, .cond-valor, .cond-ordem', function () {
            const $itemRow = $(this).closest('.condicoes-row').prev('.item-row');
            atualizarCondJson($itemRow);
        });
        // Adicionar item — mantém lógica existente mas inicializa a nova linha
        $("#add-item").click(function () {
            $('#tabela-itens tbody .condicoes-row:visible').each(function() {
                $(this).hide();
            });

            let total = $("#id_itens-TOTAL_FORMS");
            let index = parseInt(total.val());
            let html = $("#empty-itens").html().replaceAll("__prefix__", index);

            let $container = $('<tbody>').append($.parseHTML(html.trim()));
            let $itemRow = $container.find('tr.item-row').detach();
            let $condRow = $container.find('tr.condicoes-row').detach();

            let $tbody = $("#tabela-itens tbody");
            $tbody.append($itemRow);
            $tbody.append($condRow);

            total.val(index + 1);

            // Busca o select diretamente no DOM já inserido
            var $novoSelect = $tbody.find('tr.item-row').last().find('.produto-select');
            if ($novoSelect.length && !$novoSelect.hasClass('select2-hidden-accessible')) {
                $novoSelect.select2({
                    placeholder: opSel,
                    allowClear: true,
                    minimumInputLength: 1,
                    templateResult: rendOpt,
                    templateSelection: d => d.text,
                    language: lingSel,
                    ajax: ajSel2('/produtos/lista_ajax1/')
                }).on('select2:open', focSel2);
            }
        });
        // Remover linha — remove item-row E condicoes-row juntos
        $(document).on('click', '.remover-linha', function () {
            const $itemRow = $(this).closest('.item-row');
            const $condRow = $itemRow.next('.condicoes-row');
            $itemRow.find('input[type=checkbox][name$="-DELETE"]').prop('checked', true);
            $itemRow.hide();
            $condRow.hide();
        });
        // Antes do submit — garante que todos os JSONs estão atualizados
        $('form').on('submit', function () {
            $('#tabela-itens tbody .item-row:visible').each(function () {atualizarCondJson($(this));});
        });
        // Formset genérico
        function adicionarLinha(tipo){
            let total = $("#id_"+tipo+"-TOTAL_FORMS");
            let index = parseInt(total.val());
            let template = $("#empty-"+tipo).html().replaceAll("__prefix__", index);
            $("#tabela-"+tipo+" tbody").append(template);
            total.val(index + 1);
            iniciarSelect2();
        }
        // Remover linha
        $(document).on("click", ".remover-linha", function() {
                let linha=$(this).closest("tr");
                linha.find("input[type=checkbox][name$='-DELETE']").prop("checked",true);
                linha.hide();
            }
        );
        // Adicionar Condição
        $("#add-condicao").click(function(){adicionarLinha("condicoes");});
        // Controle Tipo Regra
        function controlarTipo(){
            let tipo=$("#id_tipo").val();
            // calcula quantidade
            if(tipo==="CALCULO"){
                $("#bloco-condicoes").hide();
                $("#bloco-itens").show();
            }
            // seleção automática
            else if(tipo==="SELECAO"){
                $("#bloco-condicoes").show();
                $("#bloco-itens").show();
            }
            // adicional
            else if(tipo==="ADICIONAL"){
                $("#bloco-condicoes").show();
                $("#bloco-itens").show();
            }
            // validação
            else if(tipo==="VALIDACAO"){
                $("#bloco-condicoes").show();
                $("#bloco-itens").hide();
            }
            else {
                $("#bloco-condicoes").hide();
                $("#bloco-itens").hide();
            }
        }
        $("#id_tipo").on("change", controlarTipo);
        // Simulação
        $("#btn-simular").click(function(){
            let contexto={larg_c: parseBR($("#sim-larg").val()) || 0, alt_c: parseBR($("#sim-alt").val()) || 0, peso: parseBR($("#sim-peso").val()) || 0,
                tipo_lamina: $("#sim-tipo-lamina").val(), tipo_pintura: $("#sim-tipo-pintura").val(), tem_pintura: $("#sim-tem-pintura").val()==="true"
            };
            contexto.area = contexto.larg_c * contexto.alt_c;
            $.ajax({url:"/regras-produto/simular/", method:"POST", headers:{"X-CSRFToken": $("input[name=csrfmiddlewaretoken]").val()},
                data:{regra_id: $("#id_regra").val(), contexto: JSON.stringify(contexto)},
                success:function(resp){$("#sim-resultado").html(resp.html).show();},
                error:function(){$("#sim-resultado").html("<span class='text-danger'>Erro ao simular regra.</span>");}
            });
        });
        // Inicialização
        $('#tabela-itens tbody .cond-tbody').empty();
        $('#tabela-itens tbody .condicoes-row').hide();

        $('#tabela-itens tbody .item-row').each(function () {
            iniciarSelect2(this);
        });
        controlarTipo();
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
            toast(`Selecione ao menos um produto antes de continuar!`, "warning");
            return;
        }
        $('#attTbPrecModal').modal('show');
    });
    // Adição e Remoção de quantidade de Produto (Pedidos)
    $('.remQtdP').on('click', function () {
        let qtd = parseBR($('#id_quantidadeP').val()) || 0;
        if (qtd > 0) $('#id_quantidadeP').val(formatBR((qtd - 1)));
    });
    $('.addQtdP').on('click', function () {
        let qtd = parseBR($('#id_quantidadeP').val()) || 0;
        $('#id_quantidadeP').val(formatBR((qtd + 1)));
    });
    $('.remQtdEd').on('click', function () {
        let qtd = parseBR($('#id_quantidadeEd').val()) || 0;
        if (qtd > 0) $('#id_quantidadeEd').val(formatBR(qtd - 1));
    });
    $('.addQtdEd').on('click', function () {
        let qtd = parseBR($('#id_quantidadeEd').val()) || 0;
        $('#id_quantidadeEd').val(formatBR(qtd + 1));
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
        $(this).css({'background-color': cor, 'color': corTexto, 'border': 'none', 'margin': '2px', 'padding': '0px 6px', 'border-radius': '10px', 'display': 'inline-block'});
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
                                <td>${e.fornecedor}</td><td>${e.data}</td><td>${e.entrada_id}</td><td>${e.quantidade}</td><td>R$ ${formatBR(e.valor_unitario)}</td><td><strong>R$ ${formatBR(e.total_entrada)}</strong></td>
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
        const seletorDatasGerais = '[id^="dt_pag_cr-"], [id^="cel-dt-"], [id^="dt_pag_cp-"], #data_inicio1, #data_emi_ini1, #data_emi_fim1, #data_ent_ini1, #data_ent_fim1, #data_inst_ini1, #data_inst_fim1, #data_inicio2, #data_fim2, .inp-vencimento, #data_fim1, #id_data_vencimento, #dt_efet_ent, #inpDtPriParc, #id_dt_inicio, #data, #id_dt_emi, #id_dt_prev_instalacao, #id_dt_ent, #id_dt_venc, #id_data_certificado, #id_data_emissao, #id_data_emissao1, #id_data_entrega, #id_data_nascimento_administrador, #id_data_nascimento, #id_data_doc, #id_data_prop, #id_data_aniversario, #id_dt_visita, #id_px_visita, #dtVisita, #pxVisita';
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
        iniciarLoading();
        const $modal      = $(this);
        const entradaId   = this.id.replace('efetivarModal-', '');
        const $inpParc        = $modal.find('#inpParc');
        const $inpDiasPriParc = $modal.find('#inpDiasPriParc');
        const $inpIntervalo   = $modal.find('#inpIntervalo');
        const $dtEfetivacao   = $modal.find('#dt_efet_ent');
        const $inpDtPriParc   = $modal.find('#inpDtPriParc');
        const $previewArea    = $modal.find(`#preview-parcelas-${entradaId}`);
        const $previewBody    = $modal.find(`#preview-parcelas-body-${entradaId}`);
        const $previewTotal   = $modal.find(`#preview-parcelas-total-${entradaId}`);
        // ── Valores default ──────────────────────────────────────────────
        setTimeout(() => {
            if (!$inpParc.val())        $inpParc.val('1');
            if (!$inpDiasPriParc.val()) $inpDiasPriParc.val('30');
            if (!$inpIntervalo.val())   $inpIntervalo.val('30');
            if (!$dtEfetivacao.val())   $dtEfetivacao.val(obterDataAtual2());
            if ($dtEfetivacao.val())    $inpDtPriParc.val(addDtInterv($dtEfetivacao.val(), $inpDiasPriParc.val()));
        }, 150);
        // ── Botão Gerar parcelas manualmente ────────────────────────────────
        $modal.find('.btn-gerar-parcelas').off('click.gerar').on('click.gerar', function () {
            const dtEfetiv    = $dtEfetivacao.val();
            const diasPri     = parseInt($inpDiasPriParc.val()) || '1';
            const intervalo   = parseInt($inpIntervalo.val())   || '30';
            const qtdParc     = parseInt($inpParc.val())        || '1';
            const dtPriParc   = $inpDtPriParc.val();  // DD/MM/YYYY
            const tpCobId     = $modal.find('#selTpCob').val();
            const tpCobLabel  = $modal.find('#selTpCob option:selected').text();

            if (!dtPriParc) {
                toast('Informe a data da 1ª parcela!', 'warning');
                return;
            }
            if (!tpCobId) {
                toast('Selecione um tipo de cobrança!', 'warning');
                return;
            }

            // Se já existem parcelas (do XML ou de geração anterior), confirma substituição
            if (duplicatas.length > 0) {
                if (!confirm(`Já existem ${duplicatas.length} parcela(s). Deseja substituí-las?`)) return;
            }

            // Calcula o total da entrada para dividir em partes iguais
            const totalEntrada = parseBR($modal.find('#total_entrada').val()) || 0;
            const valorParc    = totalEntrada > 0 ? (totalEntrada / qtdParc) : 0;

            // Gera as parcelas
            duplicatas = [];
            const dtBase = brParaIso(dtPriParc);

            for (let i = 0; i < qtdParc; i++) {
                const dtVenc = adicionarDias(dtBase, i === 0 ? 0 : intervalo * i);
                duplicatas.push({
                    numero:         `${String(i + 1).padStart(3, '0')}`,
                    tp_conta:       tpCobId,
                    tp_conta_label: tpCobLabel.trim(),
                    vencimento:     dtVenc,
                    valor:          valorParc.toFixed(2),
                });
            }

            renderLinhas();
            $previewArea.slideDown(200);
        });
        // ── Sincroniza Dt. 1ª Parcela com efetivação + dias ─────────────
        $modal.find('#dt_efet_ent, #inpDiasPriParc').off('change.efet').on('change.efet', function () {
            const dtEfetiv = $modal.find('#dt_efet_ent').val();
            const interv   = $modal.find('#inpDiasPriParc').val();
            if (dtEfetiv && interv) {
                $inpDtPriParc.val(addDtInterv(dtEfetiv, interv));
            }
        });
        
        // ── Carrega duplicatas do JSON embutido ──────────────────────────
        const script = document.getElementById(`cobrancas-json-${entradaId}`);
        let duplicatas = [];
        if (script) {
            try {
                duplicatas = JSON.parse(script.textContent);
            } catch (e) {
                console.error(e);
            }
        }
        if (!duplicatas.length) {
            $previewArea.hide();
            return;
        }
        // Preenche controles com os dados das duplicatas
        $inpParc.val(duplicatas.length);
        $inpIntervalo.val('');
        $inpDiasPriParc.val('');
        $inpDtPriParc.val(isoParaBrCompleto(duplicatas[0].vencimento));
        // ── Funções de renderização e recálculo ──────────────────────────
        function recalcularTotal() {
            const total = duplicatas.reduce((acc, d) => acc + (parseBR(d.valor) || 0), 0);
            $previewTotal.text(formatBR(total));
            $inpParc.val(duplicatas.length);
            // Atualiza numeração das linhas
            $previewBody.find('tr').each(function (i) {
                $(this).find('td:first').text(i + 1);
            });
        }
        function renderLinhas() {
            $previewBody.empty();
            duplicatas.forEach((dup, i) => {
                console.log(`renderLinhas — dup[${i}]:`, JSON.stringify(dup));
                const valor = parseBR(dup.valor) || 0;
                const $tr = $(`
                    <tr data-idx="${i}">
                        <td class="text-center">${i + 1}</td>
                        <td class="text-center" data-campo="numero">${dup.numero || '-'}</td>
                        <td class="text-center d-none" data-campo="num_tp_conta">
                            <input type="hidden" value="${dup.num_tp_conta || ''}">
                        </td>
                        <td class="text-center editavel" data-campo="tp_conta">
                            ${dup.tp_conta_label || dup.tp_conta || '-'}
                        </td>
                        <td class="text-center editavel" data-campo="vencimento">${isoParaBrCompleto(dup.vencimento)}</td>
                        <td class="text-end editavel" data-campo="valor">${formatBR(valor)}</td>
                        <td class="text-center">
                            <button type="button" class="btn btn-link btn-sm p-0 text-danger btn-excluir-parcela" title="Excluir parcela">
                                <i class="fa-solid fa-trash-can"></i>
                            </button>
                        </td>
                    </tr>
                `);
                $previewBody.append($tr);
            });
            recalcularTotal();
            bindEventos();
        }
        function bindEventos() {
            // ── Exclusão ────────────────────────────────────────────────
            $previewBody.find('.btn-excluir-parcela').off('click').on('click', function () {
                const idx = $(this).closest('tr').data('idx');
                if (duplicatas.length <= 1) {
                    toast('É necessário manter ao menos uma parcela!', 'warning');
                    return;
                }
                duplicatas.splice(idx, 1);
                renderLinhas();
            });
            // ── Edição inline ────────────────────────────────────────────
            $previewBody.find('td.editavel').off('click').on('click', function () {
                const $td    = $(this);
                if ($td.find('input').length) return; // já em edição
                const campo  = $td.data('campo');
                const idx    = $td.closest('tr').data('idx');
                const valAtual = duplicatas[idx][campo] || '';
                let $input;
                if (campo === 'vencimento') {
                    // Data: mostra DD/MM/YYYY e converte de/para ISO
                    $input = $(`<input type="text" class="form-control form-control-sm text-center p-0" maxlength="10" placeholder="DD/MM/AAAA" id="cel-dt-${idx}" value="${isoParaBrCompleto(valAtual)}">`);
                    $input.datepicker({
                        changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy",  monthNamesShort: ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"], dayNamesMin: ["Do", "2ª", "3ª", "4ª", "5ª", "6ª", "Sá"]
                    });
                    $input.on('blur keydown', function (e) {
                        if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== 'Escape') return;
                        if (e.key === 'Escape') {
                            renderLinhas(); return;
                        }
                        const digitado = $input.val().trim();
                        const isoNovo  = brParaIso(digitado);
                        if (!isoNovo) {
                            $input.addClass('is-invalid');
                            $input.focus();
                            return;
                        }
                        duplicatas[idx].vencimento = isoNovo;
                        renderLinhas();
                    });
                } else if (campo === 'valor') {
                    // Valor numérico
                    const numAtual = parseBR(duplicatas[idx].valor) || 0;
                    $input = $(`<input type="text" id="cel-parcela-${idx}" class="form-control form-control-sm text-end p-0" value="${formatBR(numAtual)}">`);
                    $input.on('blur keydown', function (e) {
                        if (e.type === 'keydown' && e.key !== 'Enter' && e.key !== 'Escape') return;
                        if (e.key === 'Escape') {
                            renderLinhas(); return;
                        }
                        const novo = parseBR($input.val());
                        if (isNaN(novo) || novo <= 0) {
                            $input.addClass('is-invalid');
                            $input.focus();
                            return;
                        }
                        duplicatas[idx].valor = novo.toFixed(2);
                        renderLinhas();
                    });
                } else if (campo === 'tp_conta') {
                    const opAtual  = duplicatas[idx].tp_conta       || '';
                    const lblAtual = duplicatas[idx].tp_conta_label || opAtual;
                    $input = $(`
                        <select class="form-select form-select-sm w-100" id="cel-tp-conta-${idx}">
                            ${opAtual ? `<option value="${opAtual}" selected>${lblAtual}</option>` : ''}
                        </select>
                    `);
                    $td.html($input);
                    let selecionou = false;  // ← flag para distinguir seleção de cancelamento
                    $input.select2({placeholder: opSel, allowClear: true, templateResult: rendOpt, templateSelection: d => d.text, language: lingSel, dropdownParent: $(document.body),  // ← troca aqui
                        ajax: ajSel2('/tp_cobrancas/lista_ajax/'),
                    }).on('select2:open', focSel2);
                    $input.on('select2:select', function (e) {
                        selecionou = true;
                        duplicatas[idx].tp_conta       = e.params.data.id;
                        duplicatas[idx].tp_conta_label = e.params.data.text;  // ← já vem do ajax
                        console.log('select2:select:', e.params.data);        // confirma o que vem
                        renderLinhas();
                    });
                    $input.on('select2:close', function () {
                        if (!selecionou) {
                            setTimeout(() => renderLinhas(), 200); // ← aguarda o select2:select processar
                        }
                    });
                    $input.on('select2:select', function (e) {
                        selecionou = true;  // ← marca antes de renderizar
                        duplicatas[idx].tp_conta       = e.params.data.id;
                        duplicatas[idx].tp_conta_label = e.params.data.text;
                        renderLinhas();
                    });
                    $input.on('select2:clear', function () {
                        selecionou = true;  // clear também é uma ação intencional
                        duplicatas[idx].tp_conta       = '';
                        duplicatas[idx].tp_conta_label = '';
                        renderLinhas();
                    });
                    $input.select2('open');
                    return;
                }
                $td.html($input);
                $input.focus().select();
            });
        }
        $modal.find('form').off('submit.parcelas').on('submit.parcelas', function () {
            // Remove campo anterior se existir
            $(this).find('input[name="parcelas_json"]').remove();
            console.log(duplicatas);
            // Injeta parcelas atuais
            $(this).append(
                $('<input type="hidden" name="parcelas_json">').val(JSON.stringify(duplicatas))
            );
        });
        // ── Renderização inicial ─────────────────────────────────────────
        renderLinhas();
        $previewArea.slideDown(200);
        fecharLoading();
    });
    // Limpa preview ao fechar o modal
    $(document).on('hidden.bs.modal', '[id^="efetivarModal-"]', function () {
        const entradaId = this.id.replace('efetivarModal-', '');
        $(`#preview-parcelas-body-${entradaId}`).html('');
        $(`#preview-parcelas-${entradaId}`).hide();
    });
    function brParaIso(dataBr) {
        if (!dataBr) return null;
        const partes = dataBr.split('/');
        if (partes.length !== 3) return null;
        const [dia, mes, ano] = partes;
        if (!dia || !mes || !ano || ano.length !== 4) return null;
        const d = new Date(`${ano}-${mes}-${dia}`);
        if (isNaN(d.getTime())) return null;
        return `${ano}-${mes.padStart(2,'0')}-${dia.padStart(2,'0')}`;
    }
    // Adiciona N dias a uma data ISO (YYYY-MM-DD) e retorna YYYY-MM-DD
    function adicionarDias(dataIso, dias) {
        if (!dataIso) return '';
        const d = new Date(dataIso + 'T00:00:00');
        d.setDate(d.getDate() + dias);
        const ano = d.getFullYear();
        const mes = String(d.getMonth() + 1).padStart(2, '0');
        const dia = String(d.getDate()).padStart(2, '0');
        return `${ano}-${mes}-${dia}`;
    }
    // Helper: YYYY-MM-DD → DD/MM/YYYY
    function isoParaBrCompleto(dataIso) {
        if (!dataIso) return '';
        const [ano, mes, dia] = dataIso.split('-');
        return `${dia}/${mes}/${ano}`;
    }
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
    function recalcularBaixa(modal, atualizarCampos = true) {
        const valorConta = parseBR(modal.find('[id^="valor_cr"]').val());
        const totalJurosOriginal = parseBR(modal.find('[id^="tot_juros_cr"]').val());
        const totalMultaOriginal = parseBR(modal.find('[id^="tot_multa_cr"]').val());
        const percDescJuros = parseBR(modal.find('[id^="desc_j_cr"]').val()) || 0;
        const percDescMulta = parseBR(modal.find('[id^="desc_m_cr"]').val()) || 0;
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
            valor = (parseInt(valor, 10) / 100);
            if (parseBR(valor) > 100) {valor = '100,00';}
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
            if (!formaId) return toast('Selecione uma forma!', "warning");
            if (valor <= 0) return toast('Valor inválido!', "warning");
            if (valor > restante) return toast('Valor maior que restante!', "warning");
            const gateway = select.data('gateway') || 'nenhum';
            const credencial = JSON.stringify(select.data('credencial') || {});
            tbody.append(`
                <tr data-gateway="${gateway}" data-credencial='${credencial}'>
                    <td>${formaTxt}<input type="hidden" name="forma_id[]" value="${formaId}"></td>
                    <td class="text-end">${formatBR(valor)}<input type="hidden" class="vl-item-pgto" name="forma_valor[]" value="${valor}"></td>
                    <td class="text-center">
                        <button type="button" class="btn btn-danger btn-sm remover-forma"><i class="fa-solid fa-trash"></i></button>
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
                    if (formaId && valor) {formas.push({forma_id: formaId, valor: valor});}
                });
                iniciarLoading();
                $.ajax({
                    url: `/contas_receber/${contaId}/gerar-pagamento/`, method: 'POST', data: {formas: JSON.stringify(formas), csrfmiddlewaretoken: $('[name=csrfmiddlewaretoken]').val()},
                    success: function (resp) {
                        if (resp.erro) {
                            toast(resp.erro, "error");
                            return;
                        }
                        fecharLoading();
                        abrirModalPixConta(contaId, resp);
                    }
                });
                return; // 🚫 BLOQUEIA BAIXA NORMAL
            }
            const calc = recalcularBaixa(modal);
            const form = $('<form>', {method: 'POST', action: `/contas_receber/pagar/${contaId}/`});
            form.append(`<input type="hidden" name="csrfmiddlewaretoken" value="${$('[name=csrfmiddlewaretoken]').val()}">`);
            form.append(`<input type="hidden" name="juros" value="${formatBR(calc.jurosFinal)}">`);
            form.append(`<input type="hidden" name="multa" value="${formatBR(calc.multaFinal)}">`);
            form.append(`<input type="hidden" name="desconto" value="${formatBR(calc.descontoFinal)}">`);
            modal.find('input[name="forma_id[]"], input[name="forma_valor[]"]').each(function () {form.append($(this).clone());});
            $.ajax({
                url: form.attr("action"), method: "POST", data: form.serialize(), headers: {"X-Requested-With": "XMLHttpRequest"}, success: function(resp){
                    $(".modal-baixa").modal("hide");
                    if(resp.tem_avista){
                        if(resp.imp_recibo === "Auto"){
                            window.open(resp.url_recibo, "_blank");
                            window.location = resp.redirect;
                            return;
                        }
                        if(resp.imp_recibo === "Sim"){
                            $('[id^="mdInfoBaixa-"]').modal("hide");
                            $("#modalRecibo").data("url", resp.url_recibo).data("redirect", resp.redirect).modal("show");
                            return;
                        }
                    }
                    window.location = resp.redirect;
                }
            });
        });
        function abrirModalPixConta(contaId, resp) {
            $('#pixQrContainer').html('');
            $('#statusPix').removeClass('d-none');
            $('#statusSucesso').addClass('d-none');
            $('#pixQrContainer').html(`
                <div class="mb-3">
                    <img src="data:image/png;base64,${resp.qr_base64}" width="220" class="mb-2">
                    <div class="input-group">
                        <input type="text" class="form-control text-center" value="${resp.qr_code}" readonly> data-code="${resp.qr_code}"><i class="fa-regular fa-copy"></i></button>
                    </div>
                    <strong class="d-block mt-2">R$ ${formatBR(resp.valor)}</strong>
                </div>
            `);
            $(document).off('click.copiarPix').on('click.copiarPix', '.btn-copiar', function () {
                navigator.clipboard.writeText($(this).data('code'));
                toast('Código PIX copiado!', "success");
            });
            const modalPix = new bootstrap.Modal(document.getElementById('modalPixPagamento'));
            modalPix.show();
            const interval = setInterval(() => {
                $.get(`/contas_receber/${contaId}/status-pagamento/`, function (resp) {
                    if (resp.pago) {
                        clearInterval(interval);
                        let mensagem = 'Conta recebida com sucesso!';
                        if (resp.parcial) {mensagem = `Baixa parcial realizada. Saldo restante: R$ ${formatBR(resp.restante)}`;}
                        $('#modalPixPagamento .modal-body').html(`
                            <div class="text-center py-4">
                                <div class="check-circle mx-auto"><i class="fa-solid fa-check"></i></div>
                                <h5 class="text-success fw-bold">Pagamento confirmado!</h5>
                                <p class="text-muted mb-0">Finalizando baixa...</p>
                            </div>
                        `);
                        toast(`${mensagem}`, "success");
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
            document.getElementById('modalPixPagamento').addEventListener('hidden.bs.modal', () => clearInterval(interval), { once: true });
        }
        recalcularBaixa(modal);
        const restante = atualizarRestante(modal);
        modal.find('[id^="vl_pg_cr"]').val(formatBR(restante > 0 ? restante : 0));
    });
    //  BAIXA DE CONTAS A PAGAR
    function recalcularBaixaCP(modal) {
        const valorConta       = parseBR(modal.find('[id^="valor_cp"]').val());
        const totalJurosOrig   = parseBR(modal.find('[id^="tot_juros_cp"]').val());
        const totalMultaOrig   = parseBR(modal.find('[id^="tot_multa_cp"]').val());
        const percDescJuros    = parseBR(modal.find('[id^="desc_j_cp"]').val()) || 0;
        const percDescMulta    = parseBR(modal.find('[id^="desc_m_cp"]').val()) || 0;
        const descontoJuros = totalJurosOrig * (percDescJuros / 100);
        const descontoMulta = totalMultaOrig * (percDescMulta / 100);
        const jurosFinal    = Math.max(totalJurosOrig - descontoJuros, 0);
        const multaFinal    = Math.max(totalMultaOrig - descontoMulta, 0);
        const totalPagar    = valorConta + jurosFinal + multaFinal;
        modal.find('[id^="juros_cp"]').val(formatBR(jurosFinal));
        modal.find('[id^="multa_cp"]').val(formatBR(multaFinal));
        modal.find('[id^="vl_tot_cp"]').val(formatBR(totalPagar));
        modal.find('[id^="vl_pg_cp"]').val(formatBR(totalPagar));
        return { jurosFinal, multaFinal, descontoFinal: descontoJuros + descontoMulta, totalPagar };
    }
    $(document).on('shown.bs.modal', '[id^="mdInfoBaixaCP-"]', function () {
        // Garante que é modal de CP (não de CR)
        const modal = $(this);
        if (!modal.find('[id^="valor_cp"]').length) return;
        const contaId  = modal.attr('id').split('-')[1];
        const dtPagCp  = modal.find('[id^="dt_pag_cp-"]');
        // ---------- Datepicker ----------
        if (!dtPagCp.val()) {
            dtPagCp.val(obterDataAtual2());
        }
        modal.find('[id^="desc_j_cp"], [id^="desc_m_cp"]').off('input.baixacp').on('input.baixacp', function () {
            let valor = this.value.replace(/[^\d]/g, '');
            if (!valor) valor = '0';
            valor = (parseInt(valor, 10) / 100);
            if (parseBR(valor) > 100) { valor = '100,00'; }
            this.value = valor;
            recalcularBaixaCP(modal);
        });
        // ---------- Botão Baixar → abre modal de confirmação ----------
        modal.find('.btn-baixar-cp').off('click.baixarcp').on('click.baixarcp', function () {
            // Recalcula antes de confirmar para garantir valores atualizados
            recalcularBaixaCP(modal);
            // O data-bs-toggle/target já abre o mdBaixa automaticamente
        });
        const mdBaixa = $(`#mdBaixaCP-${contaId}`);
        // ---------- Countdown no botão Sim ----------
        mdBaixa.off('shown.bs.modal.countdown').on('shown.bs.modal.countdown', function () {
            const btnConfirmar = $(this).find('.btn-confirmar');
            const spanContador = btnConfirmar.find('.contador');
            let segundos = 3;
            btnConfirmar.prop('disabled', true);
            spanContador.text(segundos);
            const timer = setInterval(function () {
                segundos--;
                spanContador.text(segundos);
                if (segundos <= 0) {
                    clearInterval(timer);
                    btnConfirmar.prop('disabled', false);
                    spanContador.text('');
                }
            }, 1000);
            // Limpa timer se modal fechar antes
            mdBaixa.one('hidden.bs.modal', function () { clearInterval(timer); });
        });
        // ---------- Submit AJAX com modal de recibo ----------
        mdBaixa.off('click.confirmarcp').on('click.confirmarcp', '.btn-confirmar-cp', function () {
            console.log('Clique confirmar');
            const form = modal.find('form');
            form.find('.campo-calc-cp').remove();
            const calc = recalcularBaixaCP(modal);
            form.append(`<input type="hidden" class="campo-calc-cp" name="juros"    value="${formatBR(calc.jurosFinal)}">`);
            form.append(`<input type="hidden" class="campo-calc-cp" name="multa"    value="${formatBR(calc.multaFinal)}">`);
            form.append(`<input type="hidden" class="campo-calc-cp" name="desconto" value="${formatBR(calc.descontoFinal)}">`);
            console.log(form.serialize());
            console.log(form.attr('action'));
            $.ajax({
                url: form.attr('action'),
                method: 'POST',
                data: form.serialize(),
                headers: { 'X-Requested-With': 'XMLHttpRequest', "X-CSRFToken": $("input[name=csrfmiddlewaretoken]").val() },
                success: function (resp) {
                    mdBaixa.modal('hide');
                    modal.modal('hide');
                    if (resp.imp_recibo === 'Auto') {
                        window.open(resp.url_recibo, '_blank');
                        window.location = resp.redirect;
                        return;
                    }
                    if (resp.imp_recibo === 'Sim') {
                        $('#modalRecibo').data('url', resp.url_recibo).data('redirect', resp.redirect).modal('show');
                        return;
                    }
                    window.location = resp.redirect;
                },
                error: function () {
                    toast('Erro ao registrar pagamento. Tente novamente.', 'error');
                }
            });
        });
        // ---------- Cálculo inicial ----------
        recalcularBaixaCP(modal);
    });
    $(document).on('click', '#simRecibo', function () {
        const modal    = $('#modalRecibo');
        const url      = modal.data('url');
        const redirect = modal.data('redirect');
        window.open(url, '_blank');
        modal.modal('hide');
        window.location = redirect;
    });
    $(document).on('click', '#naoRecibo', function () {
        const modal    = $('#modalRecibo');
        const redirect = modal.data('redirect');
        modal.modal('hide');
        window.location = redirect;
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
        let valor = $(this).val().trim();
        if (valor === "" || isNaN(valor)) {$(this).val("0,00");}
        else {$(this).val(formatBR(valor));}
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
                $(this).val("0,00");
                return;
            }
            let num = (parseBR(val) / 100);
            $(this).val(num);
        });
        $input.on("blur keydown", function(e) {
            if (e.type === "blur" || (e.type === "keydown" && e.key === "Enter")) {
                e.preventDefault();
                const novoValorRaw = $input.val().trim();
                if (novoValorRaw === "") {
                    toast(`Campo (Frete) é obrigatório!`, "warning");
                    $input.focus();
                    return;
                }
                const novoValorNum = parseBR(novoValorRaw) || 0;
                const $newSpan = $(`
                    <span class="editable" id="total-frete" style="background-color: #F08080; color: white; border-radius: 15px; padding-left: 10px; padding-right: 10px; float: right;">
                        ${formatBR(novoValorNum)}
                    </span>
                `);
                $input.replaceWith($newSpan);
                $('#id_frete').val(novoValorNum);
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
        $('#tabela-produtos tbody').each(function() {
            let vlProdTxt = $(this).find('td:nth-child(7)').text().trim();
            let vlProdNb = parseBR(vlProdTxt);
            if (!isNaN(vlProdNb)) {produtos += vlProdNb;}
            let vlDsctTxt = $(this).find('td:nth-child(6)').text().trim();
            let vlDsctNb = parseBR(vlDsctTxt);
            if (!isNaN(vlDsctNb)) {desconto += vlDsctNb;}
        });
        let freteTxt = $('#total-frete').is('input') ? $('#total-frete').val() : $('#total-frete').text();
        frete = parseBR(freteTxt) || 0;
        total = produtos + frete;
        $('#total-produtos').text('R$ ' + formatBR(produtos));
        $('#total-desconto').text('R$ ' + formatBR(desconto));
        $('#total-frete').text(formatBR(frete));
        $('#id_frete').val(formatBR(frete));
        $('#valor-total').text('R$ ' + formatBR(total));
    }
    // Pedidos
    $(document).on("click", ".editable#total-frete-p", function () {
        const $span = $(this);
        const valor = $span.text().trim();
        const $input = $(`<input type="text" id="total-frete-p" style="float: right;" class="form-control d-inline-block w-auto inpFreteP text-end fw-bold" value="${valor}">`);
        $span.replaceWith($input);
        $input.focus().select();
        $input.on("input", function() {
            let val = $(this).val().replace(/[^0-9]/g, ""); // mantém só números
            if (val === "") {
                $(this).val("0,00");
                return;
            }
            let num = (parseBR(val) / 100);
            $(this).val(num);
        });
        $input.on("blur keydown", function(e) {
            if (e.type === "blur" || (e.type === "keydown" && e.key === "Enter")) {
                e.preventDefault();
                const novoValorRaw = $input.val().trim();
                if (novoValorRaw === "") {
                    toast(`Campo (Frete) é obrigatório!`, "warning");
                    $input.focus();
                    return;
                }
                const novoValorNum = parseBR(novoValorRaw) || 0;
                const $newSpan = $(`
                    <span class="editable" id="total-frete-p" style="background-color: #F08080; color: white; border-radius: 15px; padding-left: 10px; padding-right: 10px; float: right;">
                        ${formatBR(novoValorNum)}
                    </span>
                `);
                $input.replaceWith($newSpan);
                $('#id_frete-p').val(parseBR(novoValorNum));
                calcTotalPedido();
            }
        });
    });
    function calcTotalPedido() {
        produtosP = 0;
        descontoP = 0;
        freteP = 0;
        totalP = 0;
        $('#tabela-produtos tbody tr').each(function() {
            let preco = $(this).find('input[name*="[preco_unitario]"]').val();
            let qtd   = $(this).find('input[name*="[quantidade]"]').val();
            let precoNum = parseBR(preco);
            let qtdNum   = parseBR(qtd);
            let totalBrutoItem = precoNum * qtdNum;
            produtosP += totalBrutoItem;
            let descReal = $(this).find('input[name*="[valor_desc_real]"]').val();
            let operacao = ($(this).find('input[name*="[operacao]"]').val() || '').toLowerCase();
            let descNum = parseBR(descReal);
            if (operacao === "desconto") {descontoP += descNum;}
            else {descontoP -= descNum;}
        });
        let freteTxt = $('#total-frete-p').is('input') ? $('#total-frete-p').val() : $('#total-frete-p').text();
        freteP = parseBR(freteTxt);
        totalP = produtosP - descontoP + freteP;
        $('#total-produtos-p').text('R$ ' + formatBR(produtosP));
        $('#total-desconto-p').text('R$ ' + formatBR(descontoP));
        $('#total-frete-p').text(formatBR(freteP));
        $('#id_frete-p').val(formatBR(freteP));
        $('#valor-total-p').text('R$ ' + formatBR(totalP));
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
        if (cod === "") {toast(`Código deve ser informado!`, "warning");}
        else {
            let idx = ident++;
            let codigoJaExiste = false;
            $("#tb-cod-sec tbody input[name*='[codigo]']").each(function() {
                if ($(this).val() === cod) {
                    codigoJaExiste = true;
                    return false; // sai do each
                }
            });
            if (codigoJaExiste) {toast(`O código "${cod}" já está incluso na listagem!`, "warning");}
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
    let identificador = $(".tb-prod-lista").length; // contador inicial
    let editing = false;        // flag para evitar sobrescrever margem ao editar
    let bloqueio = false;       // evita loop de eventos
    $('#id_vl_tab').on('blur', function () {
        if (bloqueio) return;
        bloqueio = true;
        const valorCompra = parseBR($('#id_vl_compra').val()) || 0;
        const valorProduto = parseBR($(this).val()) || 0;
        if (valorCompra > 0 && valorProduto > 0) {
            const margem = ((valorProduto - valorCompra) / valorCompra) * 100;
            $('#id_margem').val(margem < 0 ? '0,00' : formatInputBR(margem));
        }
        else {$('#id_margem').val('0,00');}
        bloqueio = false;
    });
    // Recalcular VALOR PRODUTO ao editar MARGEM
    $('#id_margem').on('blur', function () {
        if (bloqueio) return;
        bloqueio = true;
        const valorCompra = parseBR($('#id_vl_compra').val()) || 0;
        const margem = parseBR($(this).val()) || 0;
        if (valorCompra > 0) {
            const valorProduto = valorCompra * (1 + margem / 100);
            $('#id_vl_tab').val(formatInputBR(valorProduto));
        }
        bloqueio = false;
    });
    // Recalcular VALOR PRODUTO ao editar VALOR COMPRA
    $('#id_vl_compra').on('blur', function () {
        if (bloqueio) return;
        bloqueio = true;
        const valorCompra = parseBR($(this).val()) || 0;
        const margem = parseBR($('#id_margem').val()) || 0;
        if (valorCompra > 0 && margem !== 0) {
            const valorProduto = valorCompra * (1 + margem / 100);
            $('#id_vl_tab').val(formatInputBR(valorProduto));
        }
        bloqueio = false;
    });
    // ======= CHANGE DA TABELA =======
    $('#id_tabela').on('change', function () {
        if (editing) return; // ignora quando estiver editando
        const tp_atrib = $('#tp-atrib').val();
        const idTabela = $(this).val();
        const precoCompra = parseBR($('#id_vl_compra').val()) || 0;
        if (!idTabela) return;
        $.ajax({
            url: "/tabelas_preco/get/", method: "GET", data: { id: idTabela }, success: function(response) {
                if (response.margem !== undefined) {
                    $('#id_margem').val(formatInputBR(response.margem));
                    if (tp_atrib === "0") {$('#campo_1').val(formatInputBR(response.margem));}
                    let calc = precoCompra * (1 + response.margem / 100);
                    $('#id_vl_tab').val(formatInputBR(calc));
                }
            }, error: function() {toast(`Erro ao buscar a tabela de preço!`, "error");}
        });
    });
    $('#tb-prec').on('change', function () {
        if (editing) return; // ignora quando estiver editando
        const tp_atrib = $('#tp-atrib').val();
        const idTabela = $(this).val();
        const precoCompra = parseBR($('#id_vl_compra').val()) || 0;
        if (!idTabela) return;
        $.ajax({
            url: "/tabelas_preco/get/", method: "GET", data: { id: idTabela },
            success: function(response) {
                if (response.margem !== undefined) {
                    if (tp_atrib === "0") {$('#campo_1').val(response.margem);}
                    let calc = precoCompra * (1 + response.margem / 100);
                    $('#id_vl_tab').val(formatInputBR(calc));
                }
            }, error: function() {toast(`Erro ao buscar a tabela de preço!`, "error");}
        });
    });
    let bloqueioEnt = false;
    let editingTabEnt = false;
    $('#id_vl_tabEnt').on('blur', function () {
        if (bloqueioEnt) return;
        bloqueioEnt = true;
        const precoUnit = parseBR($('#id_preco_unit').val());
        const valorVenda = parseBR($(this).val());
        if (precoUnit > 0 && valorVenda > 0) {
            const margem = ((valorVenda - precoUnit) / precoUnit) * 100;
            $('#id_margem').val(margem < 0 ? '0,00' : formatInputBR(margem));
        }
        else {$('#id_margem').val('0,00');}
        bloqueioEnt = false;
    });
    $('#id_margem').on('blur', function () {
        if (bloqueioEnt) return;
        bloqueioEnt = true;
        const precoUnit = parseBR($('#id_preco_unit').val());
        const margem = parseBR($(this).val());
        if (precoUnit > 0) {
            const valorVenda = precoUnit * (1 + margem / 100);
            $('#id_vl_tabEnt').val(formatInputBR(valorVenda));
        }
        else {$('#id_vl_tabEnt').val('0,00');}
        bloqueioEnt = false;
    });
    $('#id_preco_unit').on('blur', function () {
        if (bloqueioEnt) return;
        bloqueioEnt = true;
        const precoUnit = parseBR($(this).val());
        const margem = parseBR($('#id_margem').val());
        if (precoUnit > 0) {
            const valorVenda = precoUnit * (1 + margem / 100);
            $('#id_vl_tabEnt').val(formatInputBR(valorVenda));
        }
        else {$('#id_vl_tabEnt').val('0,00');}
        bloqueioEnt = false;
    });
    $('#id_tabelaEnt').on('change', function () {
        if (editingTabEnt) return;
        const idTabela = $(this).val();
        const precoUnit = parseBR($('#id_preco_unit').val());
        if (!idTabela) return;
        $.ajax({
            url: "/tabelas_preco/get/", method: "GET", data: { id: idTabela }, success: function (response) {
                if (response.margem !== undefined) {
                    const margem = parseBR(response.margem);
                    $('#id_margem').val(formatInputBR(margem));
                    const valorVenda = precoUnit * (1 + margem / 100);
                    $('#id_vl_tabEnt').val(formatInputBR(valorVenda));
                }
            },
            error: function () {toast(`Erro ao buscar a tabela de preço!`, "error");}
        });
    });
    // ======= ADD / EDIT / REMOVE =======
    $('#add-tab').css('background-color', '').html('<i class="fa-solid fa-plus"></i> Incluir');
    function resetInputsTab() {
        $("#id_vl_tab, #id_vl_tabEnt, #id_margem").val("0,00");
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
            toast(`Selecione uma tabela antes de adicionar!`, "warning");
            return;
        }
        if (vl_p === "0,00" || vl_p === "" || vl_p === "0") {
            toast(`Preço de Venda deve ser informado!`, "warning");
            return;
        }
        if (trEdit) {
            let idx = trEdit.data("id");
            trEdit.find(".tb-div").html(`${tabNome}<input type="hidden" name="tab_preco[${idx}][tabela]" value="${tabId}">`);
            trEdit.find(".mg-div").html(`${formatBR(mrg)}<input type="hidden" name="tab_preco[${idx}][margem]" value="${mrg}">`);
            trEdit.find(".vl-div").html(`${formatBR(vl_p)}<input type="hidden" name="tab_preco[${idx}][vl_prod]" value="${vl_p}">`);
            trEdit = null;
            $("#id_tabela").prop("disabled", false);
            $('#add-tab').css('background-color', '').html('<i class="fa-solid fa-plus"></i> Incluir');
        } else {
            let idx = identificador++;
            $(".tb-prod-lista .vazio").remove();
            let tabelaJaExiste = false;
            $(".tb-prod-lista input[name*='[tabela]']").each(function() {
                if ($(this).val() === tabId) {
                    tabelaJaExiste = true;
                    return false;
                }
            });
            if (tabelaJaExiste) {toast(`Tabela "${tabNome}" já está inclusa na listagem!`, "warning");}
            else {
                $(".tb-prod-lista").append(`
                    <div class="list-group-item py-1 item-lista" data-id="${idx}">
                        <div class="row align-items-center linha-lista">
                            <!-- Tabela -->
                            <div class="col-md-7 fw-bold descricao-col tb-div" data-label="Tabela:">${tabNome}<input type="hidden" name="tab_preco[${idx}][tabela]" value="${tabId}"></div>
                            <!-- Margem -->
                            <div class="col-md-2 fw-semibold codigo-col mg-div" data-label="Margem:">${formatBR(mrg)}<input type="hidden" name="tab_preco[${idx}][margem]" value="${mrg}"></div>
                            <!-- Valor -->
                            <div class="col-md-2 fw-semibold codigo-col vl-div" data-label="Valor:">${formatBR(vl_p)}<input type="hidden" name="tab_preco[${idx}][vl_prod]" value="${vl_p}"></div>
                            <!-- Ações -->
                            <div class="col-md-1 text-center mb-1 mb-md-0 acoes-col">
                                <div class="btn-group btn-group-sm">
                                    <button type="button" class="editando btn btn-light btn-sm border"><i class="fas fa-edit text-success"></i></button>
                                    <button type="button" class="remover btn btn-light btn-sm border"><i class="fas fa-trash text-danger"></i></button>
                                </div>
                            </div>
                        </div>
                    </div>
                `);
            }
        }
        resetInputsTab();
    });
    // ======= REMOVER LINHA =======
    $(document).on("click", ".remover", function () {$(this).closest(".item-lista").remove();});
    // ======= EDITAR LINHA =======
    $(document).on("click", ".editando", function () {
        trEdit = $(this).closest(".item-lista");
        const idx = trEdit.data("id");
        const tabId = trEdit.find(`input[name="tab_preco[${idx}][tabela]"]`).val();
        const mrg = trEdit.find(`input[name="tab_preco[${idx}][margem]"]`).val();
        const vl_p = trEdit.find(`input[name="tab_preco[${idx}][vl_prod]"]`).val();
        editing = true; // ativa flag
        const select = $("#id_tabela");
        if (select.find(`option[value='${tabId}']`).length === 0) {
            const tabText = trEdit.find(".tb-div").text().trim();
            select.append(`<option value="${tabId}">${tabText}</option>`);
        }
        $("#id_margem").val(formatBR(mrg));
        $("#id_vl_tab").val(formatBR(vl_p));
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
            $tbody.append(`<tr class="vazio"><td colspan="4" class="text-center">Nenhuma tabela inserida.</td></tr>`);
            return;
        }
        tabelasEntTmp.forEach((item, i) => {
            let valorFmt = parseBR(item.valor);
            let margemFmt = parseBR(item.margem);
            $tbody.append(`
                <tr data-idx="${i}">
                    <td>${item.tabela_nome}</td><td>${formatBR(margemFmt)}<input type="hidden" value="${item.margem}"></td>
                    <td>${formatBR(valorFmt)}<input type="hidden" value="${item.valor}"></td>
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
        $("#id_margem").val("0,00");
        $("#id_vl_tabEnt").val("0,00");
    }
    $("#add-tabEnt").click(function () {
        let tabId = $('#id_tabelaEnt').val();
        let tabNome = $('#id_tabelaEnt option:selected').text().trim();
        let mrg = parseBR($("#id_margem").val() || "0");
        let vl_p = parseBR($("#id_vl_tabEnt").val() || "0");
        if (!tabId) {
            toast(`Selecione uma tabela antes de adicionar!`, "warning");
            return;
        }
        if (vl_p === "0,00" || vl_p === "" || vl_p === "0") {
            toast(`Preço de Venda deve ser informado!`, "warning");
            return;
        }
        if (trEditTabEnt !== null) {
            tabelasEntTmp[trEditTabEnt] = {tabela_id: tabId, tabela_nome: tabNome, margem: parseBR(mrg || 0), valor: parseBR(vl_p || 0)};
            trEditTabEnt = null;
        } else {
            let tabelaJaExiste = tabelasEntTmp.some(t => String(t.tabela_id) === String(tabId));
            if (tabelaJaExiste) {
                toast(`Tabela "${tabNome}" já está inclusa na listagem!`, "warning");
                return;
            }
            tabelasEntTmp.push({tabela_id: tabId, tabela_nome: tabNome, margem: parseBR(mrg || 0), valor: parseBR(vl_p || 0)});
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
        $("#id_margem").val(formatInputBR(item.margem));
        $("#id_vl_tabEnt").val(formatInputBR(item.valor));
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
            let valor = parseBR(t.valor);
            html += `<div class="linha-tabela-pill"><span class="tp-nome">${nome}</span><span class="tp-valor">${formatBR(valor)}</span></div>`;
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
        let qtdNum = parseBR(qtd);
        let precoNum = parseBR(preco);
        let dsctNum = parseBR(dsct);
        let total = ((precoNum * qtdNum) - dsctNum);
        if (!cod) {
            toast(`Informe o código do produto!`, "warning");
            return;
        }
        if (precoNum <= 0) {
            toast(`Preço Unitário deve ser informado!`, "warning");
            return;
        }
        if (qtdNum <= 0) {
            toast(`Quantidade deve ser informada!`, "warning");
            return;
        }
        try {await salvarTabelasProdutoAjax(cod, tabelasEntTmp);}
        catch (xhr) {
            let msg = xhr.responseJSON?.msg || "Erro ao salvar tabelas no produto.";
            toast(`${msg}`, "error");
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
            trEditando.find("td:eq(6)").text(formatBR(total));
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
                toast(`O código "${cod}" já está incluso na listagem!`, "warning");
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
                    <td style="font-weight: bold; color: #2E8B57;">${formatBR(total)}</td>
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
        $("#id_quantidade").val("1,00");
        $("#id_preco_unit").val("0,00");
        $("#id_desconto").val("0,00");
        $("#id_tabelaEnt").val("");
        $("#id_margem").val("0,00");
        $("#id_vl_tabEnt").val("0,00");
        tabelasEntTmp = [];
        trEditTabEnt = null;
        renderTabelasEntModal();
        $('#edProdModal').modal('hide');
        toast(`Registro salvo com sucesso!`, "success");
    });
    $("#cancelar-produto-lista").click(function () {
        trEditando = null;
        $("#id_desc_prod, #id_unidProduto, #id_grupoProd, #id_cod_produto, #id_marcaProd").val("");
        $("#id_quantidade").val("1,00");
        $("#id_preco_unit").val("0,00");
        $("#id_desconto").val("0,00");
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
        let qtd = trEditando.find(`input[name="produtos[${idx}][quantidade]"]`).val();
        let preco = trEditando.find(`input[name="produtos[${idx}][preco_unitario]"]`).val();
        let dsct = trEditando.find(`input[name="produtos[${idx}][desconto]"]`).val();
        tabelasEntTmp = carregarTabelasEntDaLinha(idx, trEditando) || [];
        trEditTabEnt = null;
        $("#id_cod_produto").val(cod).prop("disabled", true);
        $("#add-prod").prop("readonly", true);
        $("#id_desc_prod").val(prod);
        $("#id_quantidade").val(formatBR(qtd));
        $("#id_preco_unit").val(aplicarMascaraMoney(preco));
        $("#id_desconto").val(aplicarMascaraMoney(dsct));
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
            toast(`${e.message}`, "error");
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
        let qtdNum   = parseBR(qtd);
        let precoNum = parseBR(preco);
        let dsctNum  = parseBR(dsct);
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
        total = formatBR(total);
        // 🔥 TEXTO FORMATADO
        let sinal = atb === "desconto" ? "-" : "+";
        let cor   = atb === "desconto" ? "#dc3545" : "#198754";
        let textoDesc = "";
        // 🔥 Só mostra se for maior que ZERO
        if (dsctNum > 0) {
            if (tipo === "valor") {textoDesc = `<span style="color:${cor}; font-weight:bold;">${sinal} R$ ${dsct}</span>`;}
            else if (tipo === "percentual") {textoDesc = `<span style="color:${cor}; font-weight:bold;">${sinal} ${dsct}%</span>`;}
        }
        else {textoDesc = `<span class="text-muted fw-bold">0,00</span>`;}
        // 🔴 VALIDAÇÕES
        if (!cod) {
            toast(`Informe o código do produto!`, "warning");
            return;
        }
        if (precoNum <= 0) {
            toast(`Preço Unitário deve ser informado!`, "warning");
            return;
        }
        if (qtdNum <= 0) {
            toast(`Quantidade deve ser informada!`, "warning");
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
                toast(`O código "${cod}" já está incluso na listagem!`, "warning");
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
                        <button type="button" class="editarP btn btn-success btn-sm mt-1 mb-1"><i class="fa-solid fa-pen-to-square"></i></button>
                        <button type="button" class="remover btn btn-danger btn-sm mt-1 mb-1"><i class="fa-solid fa-trash"></i></button>
                    </td>
                </tr>
            `);
            toast(`Produto inserido com sucesso!`, "success");
        }
        // 🔄 RESET
        calcTotalPedido();
        $("#id_desc_prodP, #id_unidProdutoP, #id_grupoProdP, #id_marcaProdP, #id_cod_produtoP").val("");
        $("#id_quantidadeP").val("1.00");
        $("#id_preco_unitP, #id_vl_total_preco").val("0,00");
        $("#id_desc_acres").val("0,00");
        $("#id_alt_vlP").val("Não");
        $("#id_cod_produtoP").focus();
    });
    // Cancelar edição/adição de produto na lista de Pedidos
    $("#cancelar-produto-listaP").click(function () {
        trEditando = null;
        $("#id_desc_prodP, #id_unidProdutoP, #id_grupoProdP, #id_marcaProdP, #id_cod_produtoP").val("");
        $("#id_quantidadeP").val("1.00");
        $("#id_preco_unitP").val("0,00");
        $("#id_desc_acres").val("0,00");
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
        let qtd = parseBR(trEditando.find(`input[name="produtos[${idx}][quantidade]"]`).val());
        let preco = formatInputBR(trEditando.find(`input[name="produtos[${idx}][preco_unitario]"]`).val());
        let dsct = parseBR(trEditando.find(`input[name="produtos[${idx}][desconto]"]`).val());
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
        $("#id_desc_acres").val(parseBR(dsct));
        // 🔥 RESTAURAR SELECTS
        $("#id_tipo_desc_acres").val(tipo === "percentual" ? "Percentual" : "Valor");
        $("#id_atribuir").val(operacao === "desconto" ? "Desconto" : "Acréscimo");
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
            toast(`${e.message}`, "error");
        }
        setTimeout(() => $('#edProdModalP').modal('show'), 200);
    });
    // Função para calcular desconto/acréscimo em Pedido
    function calcularPreviewDesconto() {
        let totalBase = 0;
        $('#tabela-produtos tbody tr').each(function () {
            let preco = $(this).find('input[name*="[preco_unitario]"]').val();
            let qtd   = $(this).find('input[name*="[quantidade]"]').val();
            let precoNum = parseBR(preco);
            let qtdNum   = parseBR(qtd);
            totalBase += precoNum * qtdNum;
        });
        $('#valor-base').text('R$ ' + formatBR(totalBase));
        let tipo = $('#tipo_desconto').val();
        let operacao = $('#operacao').val();
        let valor = parseBR($('#campo_desconto').val()) || 0;
        let ajuste = 0;
        if (tipo === 'valor') {ajuste = valor;}
        else {ajuste = totalBase * (valor / 100);}
        let totalFinal = totalBase;
        if (operacao === 'desconto') {totalFinal -= ajuste;}
        else {totalFinal += ajuste;}
        if (totalFinal < 0) totalFinal = 0;
        $('#valor-final').text('R$ ' + formatBR(totalFinal));
    }
    $('#modalDesconto').on('shown.bs.modal', function () {
        $('#campo_desconto').val('0,00');
        calcularPreviewDesconto();
    });
    $('#campo_desconto, #tipo_desconto, #operacao').on('input change keyup', function () {calcularPreviewDesconto();});
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
        }, 500); // 100ms é suficiente
    });
    $('#confirmarDesconto').click(function () {
        let tipo = $('#tipo_desconto').val(); // valor | percentual
        let operacao = $('#operacao').val(); // desconto | acrescimo
        let valor = parseBR($('#campo_desconto').val()) || 0;
        if (valor < 0) {
            toast(`Informe um valor válido!`, "warning");
            return;
        }
        let totalBase = 0;
        let itens = [];
        $('#tabela-produtos tbody tr').each(function () {
            let tr = $(this);
            let preco = tr.find('input[name*="[preco_unitario]"]').val();
            let qtd   = tr.find('input[name*="[quantidade]"]').val();
            let precoNum = parseBR(preco);
            let qtdNum   = parseBR(qtd);
            let totalItem = precoNum * qtdNum;
            itens.push({tr: tr, total: totalItem});
            totalBase += totalItem;
        });
        if (totalBase <= 0) return;
        let valorTotalAjuste = 0;
        if (tipo === 'valor') {valorTotalAjuste = valor;}
        else {valorTotalAjuste = totalBase * (valor / 100);}
        let acumulado = 0;
        itens.forEach((item, index) => {
            let proporcao = item.total / totalBase;
            let valorRateado;
            if (index === itens.length - 1) {valorRateado = valorTotalAjuste - acumulado;}
            else {
                valorRateado = parseBR((valorTotalAjuste * proporcao));
                acumulado += valorRateado;
            }
            let totalFinal = item.total;
            if (operacao === "desconto") {totalFinal -= valorRateado;}
            else {totalFinal += valorRateado;}
            if (totalFinal < 0) totalFinal = 0;
            let idx = item.tr.data("id");
            let sinal = operacao === "desconto" ? "-" : "+";
            let cor;
            let texto = "";
            if (Math.abs(valorRateado) < 0.001) {
                texto = `0,00`;
                cor = "#000"; // 🔴 preto
            } else {
                cor = operacao === "desconto" ? "#dc3545" : "#198754";
                texto = tipo === "valor" ? `${sinal} R$ ${formatBR(valorRateado)}` : `${sinal} ${formatBR(((valorRateado / item.total) * 100))}%`;
            }
            item.tr.find("td:eq(4)").html(`
                <span style="color:${cor}; font-weight:bold;">${texto}</span>
                <input type="hidden" name="produtos[${idx}][desconto]" value="${formatBR(valorRateado)}">
                <input type="hidden" name="produtos[${idx}][tipo_desc]" value="valor">
                <input type="hidden" name="produtos[${idx}][operacao]" value="${operacao}">
                <input type="hidden" name="produtos[${idx}][valor_desc_real]" value="${valorRateado}">
            `);
            item.tr.find("td:eq(5)").html(`<span style="font-weight:bold; color:#2E8B57;">${formatBR(totalFinal)}</span>`);
        });
        // 🔄 RECALCULA TOTAL
        calcTotalPedido();
        $('#modalDesconto').modal('hide');
        toast(`${operacao === "desconto" ? "Desconto" : "Acréscimo"} aplicado com sucesso!`, "success");
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
        const {inputCod, desc, marca, unid, grupo, preco, precoVenda, extrasReset = [], focoFinal, aposCarregar} = config;
        // 1. Isolamos a função que faz a busca
        function executarBusca(elemento) {
            const productId = $(elemento).val();
            if (productId.trim() === '') {
                $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                return;
            }
            iniciarLoading();
            $.ajax({
                url: '/produtos/lista_ajax_ent/', method: 'GET', data: { s: productId, tp: 'cod' },
                success: async function (response) {
                    if (response.produtos.length > 0) {
                        const p = response.produtos[0];
                        $(desc).val(p.desc_prod || '');
                        $(marca).val(p.marca || '');
                        $(unid).val(p.unidProd || '');
                        $(grupo).val(p.grupo || '');
                        $(preco).val(formatBR(p.vl_compra));
                        $(precoVenda).val(formatBR(p.vl_prod));
                        // Reset campos extras
                        extrasReset.forEach(campo => {
                            $(campo.selector).val(campo.valor);
                        });
                        if (typeof aposCarregar === 'function') {aposCarregar();}
                        try {
                            const respTabs = await carregarTabelasProdutoAjax(p.id);
                            tabelasEntTmp = respTabs.tabelas || [];
                            trEditTabEnt = null;
                            renderTabelasEntModal();
                        } catch (e) {
                            tabelasEntTmp = [];
                            renderTabelasEntModal();
                        }
                        fecharLoading();
                        if (focoFinal) $(focoFinal).focus();
                    } else {
                        toast(`Código de produto não encontrado!`, "warning");
                        $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                        fecharLoading();
                    }
                },
                error: function () {
                    toast(`Erro ao buscar o produto. Tente novamente!`, "error");
                    $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                    fecharLoading();
                }
            });
        }
        // 2. Ouvinte para o evento Blur (quando sai do campo)
        $(inputCod).on('blur', function (event) {executarBusca(this);});
        // 3. Ouvinte para a tecla Enter
        $(inputCod).on('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault(); // Evita dar submit no form se houver um
                executarBusca(this);
            }
        });
    }
    function buscarProdutoCaixa(config) {
        const {inputCod, desc, marca, unid, grupo, preco, precoVenda, extrasReset = [], focoFinal, aposCarregar} = config;
        $(inputCod).on('blur', function (event) {
            const productId = $(this).val();
            if (productId.trim() === '') {
                $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                return;
            }
            $.ajax({
                url: '/produtos/lista_ajax_ent/', method: 'GET', data: { s: productId, tp: 'cod' },
                success: async function (response) {
                    if (response.produtos.length > 0) {
                        const p = response.produtos[0];
                        $(desc).val(p.desc_prod || '');
                        $(marca).val(p.marca || '');
                        $(unid).val(p.unidProd || '');
                        $(grupo).val(p.grupo || '');
                        $(preco).val(formatBR(p.vl_compra));
                        $(precoVenda).val(formatBR(p.vl_prod));
                        // Reset campos extras
                        extrasReset.forEach(campo => {
                            $(campo.selector).val(campo.valor);
                        });
                        if (typeof aposCarregar === 'function') {aposCarregar();}
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
                        toast(`Código de produto não encontrado!`, "warning");
                        $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                    }
                },
                error: function () {
                    toast(`Erro ao buscar o produto. Tente novamente!`, "error");
                    $(desc + ',' + marca + ',' + unid + ',' + grupo + ',' + preco).val('');
                }
            });
        });
    }
    // Entrada:
    buscarProduto({
    inputCod: '#id_cod_produto', desc: '#id_desc_prod', marca: '#id_marcaProd', unid: '#id_unidProduto', grupo: '#id_grupoProd', preco: '#id_preco_unit', precoVenda: '0,00', focoFinal: '#id_quantidade',
        extrasReset: [
            { selector: '#id_quantidade', valor: '0,00' },{ selector: '#id_desconto', valor: '0,00' },{ selector: '#id_margem', valor: '0,00' },{ selector: '#id_vl_tabEnt', valor: '0,00' }
        ]
    });
    // Pedido:
    buscarProduto({
    inputCod: '#id_cod_produtoP',desc: '#id_desc_prodP',marca: '#id_marcaProdP',unid: '#id_unidProdutoP',grupo: '#id_grupoProdP',preco: '0,00', precoVenda: '#id_preco_unitP',focoFinal: '#id_quantidadeP',
        extrasReset: [{ selector: '#id_desc_acresP', valor: '0,00' },{ selector: '#id_quantidadeP', valor: '1,00' },],
        aposCarregar: function () {calcularTotal();}
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
        $('#id_cod_produto, #id_cod_produtoP, #id_cod_produtoCaixa').val(id);
        $('#id_desc_prod, #id_desc_prodP, #id_desc_prodCaixa').val(desc);
        $('#id_marcaProd, #id_marcaProdP, #id_marcaProdCaixa').val(marc);
        $('#id_grupoProd, #id_grupoProdP, #id_grupoProdCaixa').val(gp);
        $('#id_unidProduto, #id_unidProdutoP, #id_unidProdutoCaixa').val(unid);
        $('#id_preco_unit').val(formatBR(vl_compra));
        $('#id_preco_unitP, #id_preco_unitCaixa').val(formatBR(vl));
        $('#produtoModal').modal('hide'); // Fecha o modal após a seleção
        $('#id_quantidade, #id_quantidadeP, #id_cod_produtoCaixa').focus();
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
                        let tituloEstoque = ""
                        if (produto.estoque_prod > 0) {
                            corEstoque = "fw-bold text-success";
                            tituloEstoque = "Saldo positivo";
                        }
                        else if (produto.estoque_prod < 0) {
                            corEstoque = "fw-bold text-danger";
                            tituloEstoque = "Saldo negativo";
                        }
                        else {
                            corEstoque = "fw-bold text-secondary";
                            tituloEstoque = "Sem saldo";
                        }
                        const row = `
                            <tr>
                                <td style="width: 10px;">
                                    <button class="btn btn-sm btn-dark prod-selec" data-id="${produto.id}" data-desc="${produto.desc_prod}" data-vl-compra="${produto.vl_compra}" data-marc="${produto.marca}" data-gp="${produto.grupo}" data-unid="${produto.unidProd}" data-vl="${produto.vl_prod}" title="Selecionar" style="margin-left: 9px;">
                                        <i class="fa-regular fa-hand-pointer"></i>
                                    </button>
                                </td>
                                <td style="width: 10px;">${produto.id}</td><td>${produto.desc_prod}</td><td style="width: 20px;">${produto.tp_prod}</td>
                                <td style="width: 20px;">${produto.marca}</td><td style="width: 20px;">${produto.grupo}</td><td style="width: 20px;">${produto.unidProd}</td>
                                <td style="width: 20px;"><span title="${tituloEstoque}" class="${corEstoque}">${formatBR(produto.estoque_prod)}</span></td>
                                <td style="width: 20px;">${formatBR(produto.vl_prod)}</td>
                            </tr>
                        `;
                        tabela.append(row);
                    });
                }
                else {tabela.append('<tr><td colspan="9" class="text-center">Nenhum produto encontrado.</td></tr>');}
                const paginacao = $('#paginacao');
                paginacao.empty();
                if (response.num_pages > 1) {
                    if (response.has_prev) {paginacao.append(`<button class="btn btn-sm btn-outline-dark pag-btn" data-page="${response.page - 1}"><i class="fa-solid fa-chevron-left"></i></button>`);}
                    for (let i = 1; i <= response.num_pages; i++) {
                        paginacao.append(`<button class="btn btn-sm ${i === response.page ? 'btn-dark' : 'btn-outline-dark'} pag-btn" data-page="${i}">${i}</button>`);
                    }
                    if (response.has_next) {paginacao.append(`<button class="btn btn-sm btn-outline-dark pag-btn" data-page="${response.page + 1}"><i class="fa-solid fa-chevron-right"></i></button>`);}
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
    $('#pesq-produtos').on('click', function() {
        iniciarLoading();
        carregarProdutos(1);
        fecharLoading();
    });
    $(document).on('click', '.pag-btn', function() {
        const page = $(this).data('page');
        iniciarLoading();
        carregarProdutos(page);
        fecharLoading();
    });
    // Teste de entrada por XML
    let xmlImportado = null;
    let xmlArquivoSelecionado = null;
    function isoParaBr(dataIso) {
        if (!dataIso) return '';
        const [ano, mes, dia] = dataIso.split('-');
        return `${dia}/${mes}/${ano}`;
    }
    $('#btn-importar-xml').on('click', function () {$('#input-xml').trigger('click');});
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
                    toast(`${resp.erro ? resp.erro : 'Erro ao ler XML.'}`, "error");
                    return;
                }
                montarModalXml(resp);
                new bootstrap.Modal(document.getElementById('xmlPreviewModal')).show();
                $('#input-xml').val('');
                fecharLoading();
            },
            error: function (xhr) {
                toast(`${xhr.responseJSON?.erro ? xhr.responseJSON?.erro : 'Erro ao ler XML.'}`, "error");
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
                    <input type="text" class="form-control form-control-sm readonly-disabled fw-bold text-end" readonly value="${formatBR(resp.nota.total)}">
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
                    <td class="text-center">${i + 1}</td><td>${item.codigo_fornecedor || ''}</td><td>${item.descricao || ''}</td><td class="text-center">${item.unidade || ''}</td>
                    <td class="text-end">${formatBR(item.quantidade)}</td><td class="text-end">${formatBR(item.valor_unitario)}</td><td class="text-end">${formatBR(item.desconto)}</td>
                    <td class="text-end">${formatBR(item.subtotal)}</td><td class="produto-vinculado-cell" style="min-width:260px;">${statusVinculo}</td>
                    <td class="text-center" style="width:90px;">
                        <div class="btn-group dropstart">
                            <button class="btn btn-outline-secondary btn-sm dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false"><i class="fa-solid fa-bars"></i></button>
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
            if (checkbox.is(':checked')) {selecionados.push({codigo: $tr.find('input[name*="[codigo]"]').val(), tr: $tr, base_calculo: getVlCompraLinhaEnt($tr)});}
        });
        return selecionados;
    }
    function getProdutosSelecionados() {
        return $('.item-lista .task-checkbox:checked').map(function () {
            const $tr = $(this).closest('tr');
            return {codigo: $(this).val(), tr: $tr, base_calculo: 0};
        }).get();
    }
    $(document).on('click', '#mdAttTbPreco', function () {
        const produtos = getProdutosSelecionados();
        if (!produtos.length) {
            console.warn("Selecione pelo menos um produto!");
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
            toast("Selecione pelo menos um produto!", "warning");
            return;
        }
        const tipo = $('#tp-atrib').val();
        const campo1 = parseBR($('#campo_1').val());
        const campo2 = parseBR($('#campo_2').val());
        if (!$('#tb-prec').val()) {
            toast("Selecione uma tabela de preço!", "warning");
            return;
        }
        if (tipo === '0' && campo1 <= 0) {
            toast("Informe uma margem válida!", "warning");
            return;
        }
        if (tipo === '1' && campo2 <= 0) {
            toast("Informe um valor válido!", "warning");
            return;
        }
        const payload = {tabela_id: $('#tb-prec').val(), tipo, campo_1: campo1, campo_2: campo2, produtos: produtos.map(p => ({id: p.codigo, base_calculo: p.base_calculo}))};
        iniciarLoading();
        try {
            const resp = await fetch('/produtos/att-tb-preco-lt/', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()}, body: JSON.stringify(payload)});
            const data = await resp.json();
            if (!data.ok) {
                toast(data.msg || 'Erro ao atualizar tabela.', "error");
                return;
            }
            produtos.forEach(p => {
                atualizarTabelaProdutoEnt(p.tr, data.tabela_nome, data.valores[String(p.codigo)]);
                p.tr.find('.task-checkbox').prop('checked', false);
            });
            $('#select-all').prop('checked', false).prop('indeterminate', false);
            updateMassChangesButton();
            toast("Tabela aplicada com sucesso!", "success");
            bootstrap.Modal.getInstance(document.getElementById('attTbPrecModal'))?.hide();
            fecharLoading();
        } catch (e) {
            console.error(e);
            toast("Erro na requisição", "error");
        } finally {
            fecharLoading();
        }
    });
    let bloqueioCalcTbPreco = false;
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
    if ($('#id_num_conta').val() != '') {$('#id_num_conta').prop('readonly', true).addClass('bg-secondary');}
    else {$('#id_num_conta').prop('readonly', false).removeClass('bg-secondary');}
    function calcularPreviewTbPreco(formatarCampos = false) {
        if (bloqueioCalcTbPreco) return;
        const produtos = getProdutosSelecionadosEnt();
        if (!produtos.length) {return;}
        const $tr = produtos[0].tr;
        const vlCompra = getVlCompraLinhaEnt($tr);
        const tipo = $('#tp-atrib').val();
        let margem = parseBR($('#campo_1').val());
        let valor = parseBR($('#campo_2').val());
        bloqueioCalcTbPreco = true;
        try {
            if (tipo === '0') {
                valor = vlCompra * (1 + (margem / 100));
                if (formatarCampos) {
                    $('#campo_1').val(formatBR(margem));
                    $('#campo_2').val(formatBR(valor));
                }
                else {$('#campo_2').val(valor);}
            } else {
                margem = vlCompra > 0 ? ((valor - vlCompra) / vlCompra) * 100 : 0;
                if (formatarCampos) {
                    $('#campo_2').val(formatBR(valor));
                    $('#campo_1').val(formatBR(margem));
                }
                else {$('#campo_1').val(margem);}
            }
        }
        finally {bloqueioCalcTbPreco = false;}
    }
    $(document).on('click', '#mdAttTbPrecoEnt', function () {
        const produtos = getProdutosSelecionadosEnt();
        if (!produtos.length) {
            toast("Selecione pelo menos um produto!", "warning");
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
        if ($('#tp-atrib').val() === '0') {calcularPreviewTbPreco(false);}
    });
    $('#campo_2').on('input keyup change', function () {
        if ($('#tp-atrib').val() === '1') {calcularPreviewTbPreco(false);}
    });
    $('#campo_1, #campo_2').on('blur', function () {calcularPreviewTbPreco(true);});
    $('#attTbPrecModalEnt form').on('submit', async function (e) {
        e.preventDefault();
        const produtos = getProdutosSelecionadosEnt();
        if (!produtos.length) {
            toast("Selecione pelo menos um produto!", "warning");
            return;
        }
        const tipo = $('#tp-atrib').val();
        const campo1 = parseBR($('#campo_1').val());
        const campo2 = parseBR($('#campo_2').val());
        if (!$('#tb-prec').val()) {
            toast("Selecione uma tabela de preço!", "warning");
            return;
        }
        if (tipo === '0' && campo1 <= 0) {
            toast("Informe uma margem válida!", "warning");
            return;
        }
        if (tipo === '1' && campo2 <= 0) {
            toast("Informe um valor válido!", "warning");
            return;
        }
        const payload = {tabela_id: $('#tb-prec').val(), tipo: $('#tp-atrib').val(), campo_1: parseBR($('#campo_1').val()), campo_2: parseBR($('#campo_2').val()),
            produtos: produtos.map(p => ({id: p.codigo, base_calculo: p.base_calculo}))
        };
        iniciarLoading();
        try {
            const resp = await fetch('/produtos/att-tb-preco-lt/', {
                method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()}, body: JSON.stringify(payload)
            });
            const data = await resp.json();
            if (!data.ok) {
                toast(data.msg || 'Erro ao atualizar tabela.', "error");
                return;
            }
            produtos.forEach(p => {
                atualizarTabelaProdutoEnt(p.tr, data.tabela_nome, data.valores[String(p.codigo)]);
                p.tr.find('.task-checkbox').prop('checked', false);
                $('#select-all').prop('checked', false).prop('indeterminate', false);
                updateMassChangesButton();
            });
            toast("Tabela aplicada com sucesso!", "success");
            bootstrap.Modal.getInstance(document.getElementById('attTbPrecModalEnt')).hide();
            fecharLoading();
        } catch (e) {
            console.error(e);
            toast("Erro na requisição", "error");
        } finally {
            fecharLoading();
        }
    });
    function atualizarTabelaProdutoEnt($tr, tabelaNome, dadosTabela) {
        const $cell = $tr.find('td').eq(7);
        const nome = String(tabelaNome || '').toUpperCase();
        const vlProd = Number(dadosTabela?.vl_prod ?? 0);
        const html = `
            <div class="linha-tabela-pill mb-1" data-tabela="${nome}">
                <span>${nome}</span> <span>${formatBR(vlProd)}</span>
            </div>
        `;
        $cell.html(html);
    }
    $(document).on('click', '#update-selected', function () {
        const itens = getItensSelecionados();
        const produtos = getProdutosSelecionados();
        if (!itens.length && !produtos.length) {
            toast(`Selecione pelo menos um item!`, "warning");
            return;
        }
        const temVinculado = itens.some(obj => {return obj.item.produto_vinculado && Number(obj.item.produto_vinculado.id);});
        if (temVinculado) {
            toast(`Existem itens já vinculados. Desmarque-os antes de continuar!`, "warning");
            return;
        }
        new bootstrap.Modal(document.getElementById('updateModal')).show();
    });
    $(document).on('click', '#update-selected-xml', function () {
        const itens = getItensSelecionados();
        const produtos = getProdutosSelecionados();
        if (!itens.length && !produtos.length) {
            toast(`Selecione pelo menos um item!`, "warning");
            return;
        }
        const temVinculado = itens.some(obj => {return obj.item.produto_vinculado && Number(obj.item.produto_vinculado.id);});
        if (temVinculado) {
            toast(`Existem itens já vinculados. Desmarque-os antes de continuar!`, "warning");
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
                toast(data.erro || 'Erro ao criar produtos.', "error");
                return;
            }
            // 🔄 atualiza tela com retorno
            data.resultados.forEach(r => {
                const produto = r.produto;
                xmlImportado.itens[r.idx].produto_vinculado = {id: produto.id, descricao: produto.descricao};
                const $tr = $(`#xml-itens-body tr[data-idx="${r.idx}"]`);
                atualizarStatusProdutoVinculado($tr, produto.id, produto.descricao);
            });
            toast(`Produtos processados com sucesso!`, "success");
        } catch (e) {
            console.error(e);
            toast('Erro na requisição', "error");
        } finally {
            bootstrap.Modal.getInstance(document.getElementById('modalCriarProdutoMassa')).hide();
            $('.task-checkbox-xml').prop('checked', false);
            $('#select-all-xml').prop('checked', false);
            fecharLoading();
        }
    });
    $(document).on('click', '#btn-criar-fornecedor-xml', function () {
        if (!xmlArquivoSelecionado) {
            toast(`Arquivo XML não encontrado para criar o fornecedor!`, "error");
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
                    toast(resp.erro || 'Erro ao criar fornecedor.', "error");
                    return;
                }
                xmlImportado.fornecedor.id = resp.fornecedor.id;
                xmlImportado.fornecedor.existe = true;
                $('#id_fornecedor').val(resp.fornecedor.id).trigger('change');
                const badgeHtml = `<label class="form-label mb-1 d-block">&nbsp;</label>
                    <span class="badge bg-success w-100 py-2">Já cadastrado</span>
                `;
                $('#btn-criar-fornecedor-xml').closest('.col-md-2').html(badgeHtml);
                toast(resp.fornecedor.ja_existia ? 'Fornecedor já existia e foi vinculado.' : 'Fornecedor criado com sucesso.', "success");
            },
            error: function (xhr) {toast(xhr.responseJSON?.erro || 'Erro ao criar fornecedor.', "error");},
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
            toast(`Informe a descrição do produto!`, "warning");
            return;
        }
        $.ajax({url: '/entradas/criar_produto_xml/', method: 'POST', contentType: 'application/json', headers: {'X-CSRFToken': $('[name=csrfmiddlewaretoken]').val()},
            data: JSON.stringify(payload), success: function (resp) {
                if (!resp.ok) {
                    toast(resp.erro || 'Erro ao cadastrar produto.', "error");
                    return;
                }
                const produto = resp.produto;
                xmlImportado.itens[idx].produto_vinculado = {id: produto.id, descricao: produto.descricao};
                const $tr = $(`#xml-itens-body tr[data-idx="${idx}"]`);
                atualizarStatusProdutoVinculado($tr, produto.id, produto.descricao);
                bootstrap.Modal.getInstance(document.getElementById('modalCriarProdutoXml')).hide();
                toast(`Produto cadastrado e vinculado!`, "success");
            },
            error: function () {toast('Erro ao cadastrar produto.', "error");}
        });
    });
    $('#btn-confirmar-vinculo-produto').on('click', function () {
        const idx = Number($('#vincular-produto-idx').val());
        const produtoId = $('#vincular-produto-select').val();
        const produtoDesc = $('#vincular-produto-select option:selected').text().trim();
        if (!produtoId) {
            toast(`Selecione um produto para vincular`, "warning");
            return;
        }
        xmlImportado.itens[idx].produto_vinculado = {id: produtoId, descricao: produtoDesc};
        const $tr = $(`#xml-itens-body tr[data-idx="${idx}"]`);
        atualizarStatusProdutoVinculado($tr, produtoId, produtoDesc);
        const modal = bootstrap.Modal.getInstance(document.getElementById('modalVincularProdutoXml'));
        if (modal) modal.hide();
        toast(`Produto vinculado com sucesso!`, "success");
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
        toast('Vínculo removido.', "warning");
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
        const qtd = parseBR(item.quantidade);
        const vlUnit = parseBR(item.preco_unitario);
        const desconto = parseBR(item.desconto);
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
                <td>${formatBR(qtd)}<input type="hidden" name="produtos[${index}][quantidade]" value="${qtd}"></td>
                <td style="font-weight: bold; color: #2E8B57;">${formatBR(vlUnit)}<input type="hidden" name="produtos[${index}][preco_unitario]" value="${vlUnit}"></td>
                <td>${formatBR(desconto)}<input type="hidden" name="produtos[${index}][desconto]" value="${desconto}"></td>
                <td style="font-weight: bold; color: #2E8B57;">${formatBR(total)}</td>
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
    $('#confirmar-importacao-xml').on('click', async function () {
        if (!xmlImportado) return;
        if (!xmlImportado.fornecedor || !xmlImportado.fornecedor.id) {
            toast(`Cadastre o fornecedor antes de confirmar a importação!`, "warning");
            return;
        }
        // ✅ NOVO: injeta o arquivo XML num input hidden do form principal
        if (xmlArquivoSelecionado) {
            const dt = new DataTransfer();
            dt.items.add(xmlArquivoSelecionado);
            document.getElementById('input-xml-entrada').files = dt.files;
        }
        if (xmlImportado?.cobranca) {
            $('#cobranca_json').val(JSON.stringify(xmlImportado.cobranca));
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
            toast(`Vincule ou cadastre os produtos antes de confirmar`, "warning");
            fecharLoading();
            return;
        }
        iniciarLoading();
        for (const [index, item] of itensOrdenados.entries()) {
            await adicionarProdutoEntradaXml({codigo: item.produto_vinculado.id, produto: item.produto_vinculado.descricao || item.descricao, quantidade: parseBR(item.quantidade || 0), preco_unitario: parseBR(item.valor_unitario || 0), desconto: parseBR(item.desconto || 0)}, index);
        }
        calcTotalEntrada();
        const previewEl = document.getElementById('xmlPreviewModal');
        const previewModal = bootstrap.Modal.getInstance(previewEl);
        if (previewModal) {
            $(previewEl).one('hidden.bs.modal', function () {
                toast('Dados do XML carregados no formulário.', "success");
                fecharLoading();
            });
            previewModal.hide();
        } else {
            toast('Dados do XML carregados no formulário.', "success");
            fecharLoading();
        }
    });
    function inicializarSelect2VinculoProdutoXml() {
        $('#vincular-produto-select').select2({
            dropdownParent: $('#modalVincularProdutoXml'), width: '100%', placeholder: 'Digite código ou descrição do produto', allowClear: true, language:lingSel,
            minimumInputLength: 1,
            ajax: {url: '/produtos/lista_ajax1/', dataType: 'json', delay: 250, data: function (params) {return {s: params.term || '', xml: 1};},
                processResults: function (data) {
                    return {results: (data.produtos || []).map(function (p) {return {id: p.id, text: `${p.id} - ${p.desc_prod}`};})};
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
                    const tipoNot = n.tipo;
                    const tipoAlerta = n.alerta_tipo;
                    let icone = '';
                    if (tipoNot === 'ALERTA') {
                        switch (tipoAlerta) {
                            case 'ESTOQUE':
                                icone = '<i class="fa-solid fa-triangle-exclamation text-warning me-2"></i>';
                                break;
                            case 'CONTA_RECEBER':
                                icone = '<i class="fa-solid fa-money-bill-wave text-success me-2"></i>';
                                break;
                            case 'CONTA_PAGAR':
                                icone = '<i class="fa-solid fa-file-invoice-dollar text-danger me-2"></i>';
                                break;
                            case 'LICENCA':
                                icone = '<i class="fa-solid fa-id-card text-primary me-2"></i>';
                                break;
                            case 'CERTIFICADO':
                                icone = '<i class="fa-solid fa-certificate text-info me-2"></i>';
                                break;
                            case 'NFE':
                                icone = '<i class="fa-solid fa-file-invoice text-secondary me-2"></i>';
                                break;
                            case 'BACKUP':
                                icone = '<i class="fa-solid fa-database text-dark me-2"></i>';
                                break;
                            default:
                                icone = '<i class="fa-solid fa-bell text-warning me-2"></i>';
                        }
                    }
                    else {icone = '<i class="fa-solid fa-walkie-talkie text-primary me-2"></i>';}
                    const titulo = tipoNot === 'ALERTA' ? (n.titulo || 'Alerta') : (n.verb || 'Notificação');
                    lista.append(`
                        <li>
                            <a href="#" class="abrir-notificacao dropdown-item text-wrap" data-tipo='${n.tipo}' data-id='${n.id}' data-alerta='${n.alerta_tipo || ''}'
                            data-solicitacao='${n.solicitacao_id || ''}' data-referencia='${n.referencia || ''}' data-titulo='${n.titulo || ''}' data-verb='${n.verb || ''}'
                            data-description='${n.description || ''}' data-url='${n.url || ''}'>
                                ${icone} ${titulo}<br>
                                <small class="text-muted">Mais informações, clique aqui!</small>
                            </a>
                        </li>
                    `);
                });
            } else {
                badge.remove();
                lista.append(`<li><a href="#" class="dropdown-item disabled text-center">Nenhuma notificação</a></li>`);
            }
        }).fail(function(xhr, status, error) {console.error('Erro ao carregar notificações:', error);});
    }
    setInterval(carregarNotificacoes, 15000);
    carregarNotificacoes();
    $(document).on('click', '.abrir-notificacao', function(e){
        e.preventDefault();
        const tipo = $(this).data('tipo');
            let icone = '';
        switch ($(this).data('alerta')) {
            case 'ESTOQUE_MINIMO' || 'ESTOQUE_MAXIMO':
                icone = '<i class="fa-solid fa-triangle-exclamation text-dark me-2"></i>';
                break;
            case 'CONTA_RECEBER':
                icone = '<i class="fa-solid fa-money-bill-wave text-success me-2"></i>';
                break;
            case 'CONTA_PAGAR':
                icone = '<i class="fa-solid fa-file-invoice-dollar text-danger me-2"></i>';
                break;
            case 'CERTIFICADO':
                icone = '<i class="fa-solid fa-certificate text-primary me-2"></i>';
                break;
            case 'BACKUP':
                icone = '<i class="fa-solid fa-database text-info me-2"></i>';
                break;
            default:
                icone = '<i class="fa-solid fa-bell me-2"></i>';
        }
        if (tipo === 'ALERTA') {
            $('#modalAlertaLabel').html(`${icone} ${$(this).data('titulo')}`);
            $('#descricaoAlerta').text($(this).data('description'));
            $('#alertaId').val($(this).data('id'));
            $('#alertaTipo').val($(this).data('alerta'));
            $('#alertaReferencia').val($(this).data('referencia'));
            // Guarda a URL no botão do modal
            $('#abrirRegistroAlerta').data('url', $(this).data('url'));
            $('#modalAlerta').modal('show');
            return;
        }
        $('#modalSolicitacaoLabel').html(`<i class="fa-solid fa-walkie-talkie me-2"></i> ${$(this).data('verb')}`);
        $('#descricaoSolicitacao').text($(this).data('description'));
        $('#solicitacaoId').val($(this).data('solicitacao'));
        $('#modalSolicitacao').modal('show');
    });
    $(document).on('click', '#abrirRegistroAlerta', function(){
        const url = $(this).data('url');
        if (url) {window.open(url, '_blank');}
        else {console.log('Alerta sem URL definida');}
    });
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
        acaoSelecionada = $btn.data('acao');
        contextoPermissao = {acao: $btn.data('acao') || '', modulo: $btn.data('modulo') || document.title, registro_id: $btn.data('registro-id') || '', registro_desc: $btn.data('registro-desc') || ''};
        verificarPermissaoAntesDeExecutar(
            permissao,
            function () {
                if ($('#createForm').length) {
                    const isOrcamento = $('.tb-prod-orc-lista').length > 0;
                    const isCaixa = $('.tb-cx-lista').length > 0;
                    // 🔥 ORÇAMENTO
                    if (isOrcamento) {
                        const temProdutos = $('.tb-prod-orc-lista .item-lista:not(.vazio)').length > 0;
                        const temAdicionais = $('.tb-adc-orc-lista .item-lista:not(.vazio)').length > 0;
                        if (!temProdutos && !temAdicionais) {
                            toast(`Insira ao menos um item antes de continuar!`, "warning");
                            $('.tb-prod-orc-lista').addClass('border border-warning');
                            setTimeout(() => {
                                $('.tb-prod-orc-lista').removeClass('border border-warning');
                            }, 1500);
                            return;
                        }
                    }
                    // 🔥 CAIXA (SEU CASO NOVO)
                    else if (isCaixa) {
                        const semItensArray = !itens || itens.length === 0;
                        const semItensDOM = $('.tb-cx-lista .item-lista').length === 0;   // ✅ inverte o sinal
                        if (semItensArray || semItensDOM) {
                            toast(`Insira ao menos um produto antes de continuar!`, "warning");
                            $('.tb-cx-lista').addClass('border border-warning');
                            setTimeout(() => {
                                $('.tb-cx-lista').removeClass('border border-warning');
                            }, 1500);
                            return;
                        }
                    }
                    // 🔥 FORM PADRÃO
                    else {
                        if ($('#tabela-produtos tbody tr').length === 0 || $('#tabela-produtos tbody tr.vazio').length) {
                            toast(`Insira ao menos um produto antes de continuar!`, "warning");
                            $('#tabela-produtos').addClass('border border-warning');
                            setTimeout(() => {
                                $('#tabela-produtos').removeClass('border border-warning');
                            }, 1500);
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
                    $.post(url, function () {location.reload();}).fail(function () {toast(`Erro ao tentar executar a ação!`, "error");});
                }
                else if (href) {window.location.href = href;}
                else if (acaoSelecionada === "atribuir_desconto") {$('#modalDesconto').modal('show');}
                else if (acaoSelecionada === "atribuir_acrescimo") {$('#modalAcrescimo').modal('show');}
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
                    if (!modalEl) {modalEl = document.getElementById('faturarModal-' + id);}
                    const modalMenuEl = document.getElementById('menuModal' + id);
                    if (modalMenuEl) {
                        const menuInstance = bootstrap.Modal.getInstance(modalMenuEl);
                        if (menuInstance) {menuInstance.hide();}
                    }
                    if (modalEl) {
                        const modal = new bootstrap.Modal(modalEl, {keyboard: false});
                        modal.show();
                    }
                }
            },
            function () {
                fecharLoading();
                toast(`${msgNegado}`, "warning");
                if (acaoSelecionada) {$('#confirmModal').modal('show');}
            }
        );
    });
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
                toast(`Tempo expirado. A solicitação não foi respondida!`, "default");
                carregarNotificacoes();
                return;
            }
            $.get(`/orcamentos/verificar-solicitacao/${solicitacaoId}/`, function(data) {
                if (data.status === 'Aprovada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast(`Solicitação Concedida ao usuário!`, "success");
                    if (acaoSelecionada === "atribuir_desconto") {$('#modalDesconto').modal('show');}
                    else if (acaoSelecionada === "atribuir_acrescimo") {$('#modalAcrescimo').modal('show');}
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
                } else if (data.status === 'Negada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast(`Solicitação Negada ao usuário!`, "error");
                } else if (data.status === 'Expirada') {
                    clearInterval(timer);
                    if (toastAguardando) toastAguardando.hideToast();
                    toast(`A solicitação expirou!`, "default");
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
            data.usuarios.forEach(u => {select.append(`<option value="${u.codigo_local}">${u.nome}</option>`);});
        });
    });
    $('#liberarAgora').on('click', function () {
        const usuarioId = $('#userSelect').val();
        const senha = $('#senhaLiberacao').val();
        if (!usuarioId) {
            toast(`Usuário deve ser informado!`, "warning");
            return;
        }
        if (!senha) {
            toast(`Digite a senha do Usuário Autorizador!`, "warning");
            return;
        }
        $.ajax({
            url: '/orcamentos/liberar-com-senha/', type: 'POST', data: {usuario_id: usuarioId, senha: senha, acao: acaoSelecionada, csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val()},
            success: function (resp) {
                if (resp.status === 'Aprovada') {
                    $('#userSelectModal').modal('hide');
                    toast(`Solicitação Concedida ao usuário!`, "success");
                    fecharLoading();
                    console.log("acaoSelecionada =", acaoSelecionada);
                    if (acaoSelecionada === "atribuir_desconto") {$('#modalDesconto').modal('show');}
                    else if (acaoSelecionada === "atribuir_acrescimo") {$('#modalAcrescimo').modal('show');}
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
                    if (window.acaoCallback) {window.acaoCallback();}
                }
                else {
                    toast(`Senha inserida incorreta!`, "error");
                    fecharLoading();
                }
            }
        });
        $('#senhaLiberacao').val('');
    });
    $(document).on("keydown", "#senhaLiberacao", function(e) {
        if (e.key === "Enter") {
            e.preventDefault();
            $("#liberarAgora").click();
            iniciarLoading();
        }
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
            toast(`ID da solicitação não encontrado!`, "default");
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
            if (response.status === "Aprovada") {toast(`Solicitação Concedida ao usuário!`, "success");}
            else {toast(`Solicitação Negada ao usuário!`, "error");}
        });
        carregarNotificacoes();
    }
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
            total = parseBR(total || 0);
            parcelas = parseInt(parcelas || 1, 10);
            if (!parcelas || parcelas <= 1) return [parseBR(total)];
            const base = Math.floor((total / parcelas) * 100) / 100;
            let soma = 0;
            const vals = [];
            for (let i = 0; i < parcelas - 1; i++) {
                vals.push(parseBR(base));
                soma += base;
            }
            vals.push(parseBR((total - soma)));
            return vals;
        }
        function montarNumeroConta(numOrc, totalParc, parcAtual) {return `${numOrc}/${String(totalParc).padStart(2, '0')}-${String(parcAtual).padStart(1, '0')}`;}
        function initDatepickerCampo($campo) {
            if (!$campo.length || $campo.hasClass('hasDatepicker')) return;
            $campo.datepicker({changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy",
                monthNamesShort: ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"], dayNamesMin: ["Do","2ª","3ª","4ª","5ª","6ª","Sá"],
                beforeShow: function (input) {
                    const $input = $(input);
                    if ($input.hasClass('dt-fat-orcamento')) {
                        const $modal = $input.closest('.modal-faturar-orcamento');
                        const editando = $modal.find('.btn-lib-dt-fat').attr('data-editando') === '1';
                        if (!editando) return false;
                    }
                    if ($input.hasClass('inp-vencimento')) {
                        const $tr = $input.closest('tr');
                        const editando = $tr.find('.btn-toggle-edicao').attr('data-editando') === '1';
                        if (!editando) return false;
                    }
                    setTimeout(function () {
                        $('.ui-datepicker').css('z-index', 2000);
                    }, 0);
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
                dados.push({forma_pgto_id: $tr.data('formaId'), num_conta: $tr.find('.inp-num-conta').text().trim(), valor: parseBR($tr.find('.inp-valor').val()), data_vencimento: $tr.find('.inp-vencimento').val()});
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
                const valor = parseBR(valorBruto);
                const geraParcelas = parseInt($linha.data('geraParcelas') || 0, 10) === 1;
                const parcelas = geraParcelas ? parseInt($linha.data('parcelas') || 1, 10) : 1;
                const intervalo = geraParcelas ? parseInt($linha.data('intervalo') || 0, 10) : 0;
                const valores = splitValue(valor, parcelas);
                for (let i = 1; i <= parcelas; i++) {
                    const venc = new Date(fatura);
                    venc.setDate(venc.getDate() + (intervalo * i));
                    html += `
                        <tr data-preview-row="1" data-forma-id="${formaId}">
                            <td><span class="inp-num-conta">${montarNumeroConta(numOrcamento, parcelas, i)}</span></td>
                            <td><input type="text" class="form-control form-control-sm inp-valor" value="${formatBR(valores[i - 1])}" readonly></td>
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
                const valor = parseBR($(this).find('.inp-valor').val());
                soma += valor;
            });
            $total.text('R$ ' + formatBR(soma));
        }
        $(document).on('input', '.inp-valor', function () {formatInputBR($(this));});
        $(document).on('blur', '.inp-valor', function () {
            const valor = parseBR($(this).val()) || 0;
            $(this).val(formatBR(valor));
        });
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
                    toast(`${msgNegado}`, "warning");
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
                function () {toast(`${msgNegado}`, "warning");}
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
                if (typeof valorRaw === 'string') {valorRaw = valorRaw.replace(/\./g, '');}
                const valor = parseBR(valorRaw) || 0;
                console.log("DEBUG FORMA:", {gateway, valor, forma_id: $row.data('forma-id')});
                if (gateway && gateway !== 'nenhum' && gateway !== 'none') {
                    temGateway = true;
                    formasGateway.push({forma_id: $row.data('forma-id'), valor: valor});
                }
            });
            // 🚨 NÃO tem gateway → fluxo normal
            if (!temGateway) {
                $.ajax({
                    url: $btn.closest("form").attr("action"), method: "POST", data: $btn.closest("form").serialize(), headers: {"X-Requested-With": "XMLHttpRequest"},
                    success: function(resp){
                        $(".modal-faturar-orcamento").modal("hide");
                        if(resp.tem_avista){
                            if(resp.imp_recibo === "Auto"){
                                window.open(resp.url_recibo, "_blank");
                                window.location = resp.redirect;
                                return;
                            }
                            if(resp.imp_recibo === "Sim"){
                                $("#modalRecibo").data("url", resp.url_recibo);
                                $("#modalRecibo").data("redirect", resp.redirect);
                                $("#modalRecibo").modal("show");
                                return;
                            }
                        }
                        window.location = resp.redirect;
                        toast('Orçamento faturado com sucesso!', 'success');
                    }
                });
                return;
            }
            // ⚡ TEM gateway → gerar pagamento
            iniciarLoading();
            $.ajax({
                url: `/orcamentos/${orcamentoId}/gerar-pagamento/`, method: 'GET', success: function (resp) {
                    fecharLoading();
                    if (!resp.pagamentos || !resp.pagamentos.length) {
                        toast(`Nenhum pagamento foi gerado!`, "error");
                        return;
                    }
                    // 👉 abre modal PIX
                    abrirModalPixOrcamento(resp.pagamentos, orcamentoId);
                },
                error: function () {toast(`Erro ao gerar pagamento!`, "error");}
            });
        });
        function abrirModalPixOrcamento(pagamentos, orcamentoId) {
            let html = '';
            pagamentos.forEach(p => {
                const valor = parseBR(p.valor || 0);
                html += `
                    <div class="mb-3 text-center">
                        <img src="data:image/png;base64,${p.qr_base64}" width="220" class="mb-2">
                        <div class="input-group">
                            <input type="text" class="form-control text-center" value="${p.qr_code}" readonly>
                            <button class="btn btn-outline-secondary btn-copiar" data-code="${p.qr_code}"><i class="fa-regular fa-copy"></i></button>
                        </div>
                        <strong class="d-block mt-2">R$ ${formatBR(valor)}</strong>
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
                toast(`Código PIX copiado!`, "success");
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
                                <div class="check-circle mx-auto"><i class="fa-solid fa-check"></i></div>
                                <h5 class="text-success fw-bold">Pagamento confirmado!</h5>
                                <p class="text-muted mb-0">Finalizando Orçamento...</p>
                            </div>
                        `;
                        toast(`Pagamento aprovado!`, "success");
                        // 🔥 chama faturamento automático
                        faturarOrcamentoAposPagamento(orcamentoId, modalPix);
                    }
                });
            }, 3000);
        }
        function faturarOrcamentoAposPagamento(orcamentoId, modalPix) {
            $.post(`/orcamentos/fat.orc/${orcamentoId}/`, {csrfmiddlewaretoken: getCSRFToken()}).done(function () {
                toast(`Orçamento faturado com sucesso!`, "success");
                setTimeout(() => {
                    modalPix.hide();
                    $('.modal-faturar-orcamento').modal('hide');
                    iniciarLoading();
                    setTimeout(() => {
                        window.location.href = `/orcamentos/lista/?s=${orcamentoId}&sit=Faturado`;
                    }, 1500);
                }, 1500);
            }).fail(function () {toast(`Erro ao faturar orçamento!`, "error");});
        }
    });
    $("#simRecibo").click(function(){
        const modal = $("#modalRecibo");
        window.open(modal.data("url"), "_blank");
        window.location = modal.data("redirect");
    });
    $("#naoRecibo").click(function(){window.location = $("#modalRecibo").data("redirect");});
    // Teste para Faturamento de Pedidos
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
        function initDatepickerCampo($campo) {
            if (!$campo.length || $campo.hasClass('hasDatepicker')) return;
            $campo.datepicker({changeMonth: true, changeYear: true, dateFormat: "dd/mm/yy", monthNamesShort: ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"],
                dayNamesMin: ["Do","2ª","3ª","4ª","5ª","6ª","Sá"],
                beforeShow: function (input) {
                    const $input = $(input);
                    // 🔥 FATURAMENTO PEDIDO
                    if ($input.hasClass('dt-fat-pedido')) {
                        const $modal = $input.closest('.modal-faturar-pedido');
                        const editando = $modal.find('.btn-lib-dt-fat-ped').attr('data-editando') === '1';
                        if (!editando) return false;
                    }
                    // 🔥 PARCELAS PEDIDO
                    if ($input.hasClass('inp-vencimento')) {
                        const $tr = $input.closest('tr');
                        const editando = $tr.find('.btn-edit-parcela').attr('data-editando') === '1';
                        if (!editando) return false;
                    }
                    setTimeout(function () {
                        $('.ui-datepicker').css('z-index', 2000);
                    }, 0);
                }
            });
        }
        function setEstadoBotaoDataFatPedido($modal, editando) {
            const $campo = $modal.find('.dt-fat-pedido');
            const $btn = $modal.find('.btn-lib-dt-fat-ped');
            $btn.attr('data-editando', editando ? '1' : '0');
            if (editando) {
                $campo.removeAttr('readonly');
                $btn.removeClass('btn-outline-secondary').addClass('btn-success').html('<i class="fa fa-check"></i>');
            } else {
                $campo.attr('readonly', true);
                $btn.removeClass('btn-success').addClass('btn-outline-secondary').html('<i class="fa fa-pen"></i>');
            }
        }
        function splitValue(total, parcelas) {
            const base = Math.floor((total / parcelas) * 100) / 100;
            let soma = 0, arr = [];
            for (let i = 0; i < parcelas - 1; i++) {
                arr.push(base);
                soma += base;
            }
            arr.push(total - soma);
            return arr;
        }
        function getContext($modal) {
            return {id: $modal.data('pedidoId') || $modal.data('id') || 0, tipo: $modal.hasClass('modal-faturar-pedido') ? 'pedido' : 'caixa'};
        }
        function getTotalPedido($modal) {return parseBR($modal.find('.totalModal').val());}
        function getTotalFormas($modal) {
            let soma = 0;
            $modal.find('.table-formas tbody tr').each(function () {
                soma += parseBR($(this).data('valor'));
            });
            return soma;
        }
        function atualizarSaldo($modal) {
            const total = getTotalPedido($modal);
            const pago = getTotalFormas($modal);
            const saldo = total - pago;
            const $input = $modal.find('.inp-valor-pgto');
            const $saldo = $modal.find('.saldo-restante');
            $saldo.removeClass('saldo-ok saldo-erro saldo-animar');
            void $saldo[0].offsetWidth;
            if (Math.abs(saldo) < 0.001) {$saldo.html('<i class="fa-solid fa-check"></i> Sem Saldo Restante! ').addClass('saldo-ok saldo-animar');}
            else if (saldo < 0) {
                const troco = Math.abs(saldo);
                $saldo.html('<i class="fa-solid fa-sack-dollar"></i> Troco: R$ ' + formatBR(troco)).addClass('saldo-ok saldo-animar');
            }
            else {$saldo.html('<i class="fa-solid fa-triangle-exclamation"></i> Saldo Restante: R$ ' + formatBR(saldo)).addClass('saldo-erro saldo-animar');}
            $input.val(formatBR(saldo));
        }
        $("#finalizarVendaBtn").click(function(){
            const $modal = $('.modal-pagamento');
            atualizarSaldo($modal);
        });
        function gerarParcelas($modal) {
            const $tbody = $modal.find('.preview-table tbody');
            $tbody.empty();
            let tem = false;
            const baseDate = new Date();
            $modal.find('.table-formas tbody tr').each(function () {
                const parcelas = parseInt($(this).data('parcelas'));
                const dias = parseInt($(this).data('dias'));
                const valor = parseBR($(this).data('valor'));
                if (parcelas < 1 || $(this).data('gera') != 1) return;
                tem = true;
                const valores = splitValue(valor, parcelas);
                for (let i = 1; i <= parcelas; i++) {
                    let dt = new Date(baseDate);
                    dt.setDate(dt.getDate() + (dias * i));
                    const numeroParcela = `${String(parcelas).padStart(2, '0')}-${i}`;
                    $tbody.append(`
                        <tr>
                            <td>${i}/${numeroParcela}</td>
                            <td><input class="form-control form-control-sm inp-valor" value="${formatBR(valores[i - 1])}" readonly></td>
                            <td><input class="form-control form-control-sm inp-vencimento" value="${formatDateInput(dt)}" readonly></td>
                            <td><button class="btn btn-warning btn-sm btn-edit-parcela"><i class="fa fa-pen"></i></button></td>
                        </tr>
                    `);
                }
            });
            $modal.find('.preview-table, .preview-title').toggleClass('d-none', !tem);
            $tbody.find('.inp-vencimento').each(function () {initDatepickerCampo($(this));});
        }
        $(document).on('click', '.btn-lib-dt-fat-ped', function (e) {
            e.preventDefault();
            e.stopPropagation();
            const $btn = $(this);
            const $modal = $btn.closest('.modal-faturar-pedido');
            const permissao = $btn.data('permissao');
            const msgNegado = $btn.data('msg-negado') || 'Sem permissão para alterar data.';
            const editando = $btn.attr('data-editando') === '1';
            verificarPermissaoAntesDeExecutar(
                permissao,
                function () {
                    setEstadoBotaoDataFatPedido($modal, !editando);
                    if (!editando) {
                        const $campo = $modal.find('.dt-fat-pedido');
                        $campo.focus();
                        try {$campo.datepicker('show');}
                        catch(e){}
                    }
                },
                function () {toast(`${msgNegado}`, "warning");}
            );
        });
        $(document).on('change', '.dt-fat-pedido', function () {
            const $modal = $(this).closest('.modal-faturar-pedido');
            const editando = $modal.find('.btn-lib-dt-fat-ped').attr('data-editando') === '1';
            if (!editando) return;
            const novaData = parseBrDate($(this).val());
            if (!novaData) return;
            let linhaGlobal = 0;
            // 🔥 percorre formas
            $modal.find('.table-formas tbody tr').each(function () {
                const $forma = $(this);
                const parcelas = parseInt($forma.data('parcelas') || 0);
                const dias = parseInt($forma.data('dias') || 0);
                const gera = parseInt($forma.data('gera') || 0);
                if (!gera || parcelas < 1) return;
                for (let i = 1; i <= parcelas; i++) {
                    let dt = new Date(novaData);
                    dt.setDate(dt.getDate() + (dias * i));
                    const $linhaPreview = $modal.find('.preview-table tbody tr').eq(linhaGlobal);
                    $linhaPreview.find('.inp-vencimento').val(formatDateInput(dt));
                    linhaGlobal++;
                }
            });
        });
        $(document).on('click', '.btn-canc-fat-pedido', function () {
            const $modal = $(this).closest('.modal-faturar-pedido');
            limparTabelaFormas($modal);
            $modal.find('.preview-table tbody').empty();
            $modal.find('.preview-table, .preview-title').addClass('d-none');
            $modal.find('.inp-valor-pgto').val('');
            $modal.find('.dt-fat-pedido').val('');
            setEstadoBotaoDataFatPedido($modal, false);
        });
        $(document).on('shown.bs.modal', '.modal-faturar-pedido', function () {
            const $modal = $(this);
            const $campo = $modal.find('.dt-fat-pedido');
            initDatepickerCampo($campo);
            setEstadoBotaoDataFatPedido($modal, false);
        });
        // 🔥 MOSTRAR PARCELAS / CONFIG FORMA
        $(document).on('change', '[id^=formaPgtoSelect-], .forma-pgto', function () {
            const $select = $(this);
            const id = $select.val();
            const $modal = $select.closest('.modal');
            if (!id) return;
            $.get('/formas_pgto/forma-pgto-info/' + id + '/', function (data) {
                const ehPrazo = (data.tipo || '').toLowerCase() === 'a prazo';
                // 🔥 mostra parcelas só se for a prazo
                $modal.find('.campos-parcela').toggleClass('d-none', !ehPrazo);
                if (ehPrazo) {
                    // padrão mínimo
                    if (parseInt($modal.find('.parcelasPgto').val() || 0) < 1) {$modal.find('.parcelasPgto').val(1);}
                    if (parseInt($modal.find('.diasPgto').val() || 0) <= 0) {$modal.find('.diasPgto').val(30);}
                } else {
                    // 🔥 À VISTA = SEM PARCELA
                    $modal.find('.parcelasPgto').val(0);
                    $modal.find('.diasPgto').val(0);
                }
                $select.data('gateway', data.gateway || 'nenhum');
                $select.data('credencial', data.credenciais || null);
                $select.data('troco', data.troco ? 1 : 0);
                $select.data('gera', ehPrazo ? 1 : 0);
                $select.data('tipo', data.tipo || '');
            });
        });
        // 🚀 ADD FORMA (COM TODAS VALIDAÇÕES)
        $(document).on('click', '.btn-add-forma', function () {
            const $modal = $(this).closest('.modal');
            const $select = $modal.find('[id^=formaPgtoSelect-], .forma-pgto');
            const formaId = $select.val();
            const formaDesc = $select.find('option:selected').text();
            const valor = $modal.find('.inp-valor-pgto').val();
            const valorNum = parseBR(valor) || 0;
            const parcelas = parseInt($modal.find('.parcelasPgto').val() || 1);
            const dias = parseInt($modal.find('.diasPgto').val() || 0);
            const geraParcelas = $select.data('gera') == 1;
            const permiteTroco = $select.data('troco') == 1;
            const gateway = $select.data('gateway') || 'nenhum';
            const credencial = $select.data('credencial');
            if (!formaId || !valor) {
                toast(`Informe a forma e o valor!`, "warning");
                return;
            }
            if ($select.data('troco') === undefined) {
                toast(`Aguarde o carregamento dos dados da forma!`, "default");
                return;
            }
            if ($select.data('gateway') === undefined) {
                toast(`Aguarde o carregamento dos dados da forma!`, "default");
                return;
            }
            if (valorNum <= 0) {
                toast(`Valor informado inválido!`, "warning");
                return;
            }
            iniciarLoading();
            const $tbody = $modal.find('.table-formas tbody');
            const jaExiste = $tbody.find('tr').filter(function () {
                return $(this).data('forma') == formaId;
            }).length > 0;
            if (jaExiste) {
                toast('Forma de pagamento já adicionada!', 'warning');
                return;
            }
            const index = $tbody.children().length + 1;
            $tbody.append(`
                <tr data-forma="${formaId}" data-valor="${valorNum}" data-parcelas="${geraParcelas ? parcelas : 0}" data-dias="${geraParcelas ? dias : 0}"
                    data-gera="${geraParcelas ? 1 : 0}" data-troco="${permiteTroco ? 1 : 0}" data-gateway="${gateway}" data-credencial='${JSON.stringify(credencial)}'>
                    <td>${index}</td><td>${formaDesc}</td><td>${formatBR(valorNum)}</td><td>${geraParcelas ? parcelas : '-'}</td><td>${geraParcelas ? dias : '-'}</td>
                    <td><button class="btn btn-danger btn-sm btn-remove-forma"><i class="fa fa-trash"></i></button></td>
                </tr>
            `);
            gerarParcelas($modal);
            atualizarSaldo($modal);
            const total = getTotalPedido($modal);
            const pago = getTotalFormas($modal);
            const saldo = total - pago; // 🔥 padrão
            let permiteTrocos = false;
            // verifica se alguma forma permite troco
            $modal.find('.table-formas tbody tr').each(function () {
                if ($(this).attr('data-troco') == "1") {permiteTrocos = true;}
            });
            // 🔥 TEM TROCO
            if (saldo < 0) {
                if (!permiteTrocos) {
                    toast(`Forma de pagamento não permite troco!`, "warning");
                    return;
                }
                troco = Math.abs(saldo);
            }
            $modal.find('.inp-valor-pgto').val(saldo > 0 ? formatBR(saldo) : '0,00');
            $modal.find('.parcelasPgto').val(1);
            $modal.find('.diasPgto').val(30);
            $modal.find('.campos-parcela').addClass('d-none');
            $select.val('').trigger('change');
            fecharLoading();
        });
        // ❌ REMOVE FORMA
        $(document).on('click', '.btn-remove-forma', function () {
            const $modal = $(this).closest('.modal');
            $(this).closest('tr').remove();
            $modal.find('.table-formas tbody tr').each(function (i) {
                $(this).find('td:first').text(i + 1);
            });
            gerarParcelas($modal);
            atualizarSaldo($modal);
            // 🔥 FOCO + ABRIR SELECT2
            const $select = $modal.find('.forma-pgto');
            setTimeout(() => {
                $select.select2('open');
            }, 100);
        });
        function limparTabelaFormas($modal) {
            // remove todas as linhas
            $modal.find('.table-formas tbody').html('');
            // recalcula parcelas e saldo
            gerarParcelas($modal);
            atualizarSaldo($modal);
            // foco no select2
            const $select = $modal.find('.forma-pgto');
            setTimeout(() => {
                $select.select2('open');
            }, 100);
        }
        // ✏️ EDITAR PARCELA
        $(document).on('click', '.btn-edit-parcela', function () {
            const $btn = $(this);
            const $tr = $btn.closest('tr');
            const editando = $btn.attr('data-editando') === '1';
            const $valor = $tr.find('.inp-valor');
            const $venc = $tr.find('.inp-vencimento');
            if (!editando) {
                $valor.removeAttr('readonly');
                $venc.removeAttr('readonly');
                $btn.attr('data-editando', '1').removeClass('btn-warning').addClass('btn-success').html('<i class="fa fa-check"></i>');
            } else {
                $valor.attr('readonly', true);
                $venc.attr('readonly', true);
                $btn.attr('data-editando', '0').removeClass('btn-success').addClass('btn-warning').html('<i class="fa fa-pen"></i>');
            }
        });
        $(document).on('shown.bs.modal', '.modal-pagamento', function () {
            iniciarLoading();
            let modal = $(this);
            if (modal.find('.table-formas tbody tr').length > 0) {
                fecharLoading();
                return;
            }
            let select = modal.find('.forma-pgto');
            let inputValor = modal.find('.inp-valor-pgto');
            let btnAdd = modal.find('.btn-add-forma');
            let total = parseBR(modal.find('.totalModal').val()) || 0;
            $.get('/formas_pgto/forma-padrao/', function (resp) {
                if (!resp.id) return;
                let option = new Option(resp.text, resp.id, true, true);
                select.append(option).trigger('change');
                // 🔥 CORREÇÃO AQUI
                inputValor.val(formatBR(total));
                setTimeout(() => {
                    btnAdd.click();
                }, 400);
            });
        });
        // ✅ CONFIRMAR (CAIXA + PEDIDO)
        $(document).on('click', '.btn-confirmar-pedido', function (e) {
            e.preventDefault();
            const $modal = $(this).closest('.modal');
            const ctx = getContext($modal);
            let formas = [];
            let parcelas = [];
            $modal.find('.table-formas tbody tr').each(function () {
                formas.push({forma:$(this).data('forma'),valor:parseBR($(this).data('valor')),parcelas:parseInt($(this).data('parcelas')),dias:parseInt($(this).data('dias'))});
            });
            $modal.find('.preview-table tbody tr').each(function () {
                parcelas.push({numero: $(this).find('td:eq(0)').text(), valor: $(this).find('.inp-valor').val(), vencimento: $(this).find('.inp-vencimento').val()});
            });
            if (ctx.tipo === 'pedido') {
                let formasNormais = [];
                let formasGateway = [];
                $modal.find('.table-formas tbody tr').each(function () {
                    const gateway = $(this).data('gateway');
                    const valor = parseBR($(this).data('valor') || 0);
                    if (valor <= 0) return;
                    const obj = {forma: $(this).data('forma'), valor: valor, parcelas: parseInt($(this).data('parcelas') || 1), dias: parseInt($(this).data('dias') || 0)};
                    if (gateway && gateway !== 'nenhum') {formasGateway.push(obj);}
                    else {formasNormais.push(obj);}
                });
                // 🔥 PRIORIDADE TOTAL PARA PIX (gateway)
                if (formasGateway.length > 0) {
                    $.get(`/pedidos/${ctx.id}/recuperar-pagamento/`, function (resp) {
                        if (!resp.erro && resp.qr_code) {
                            toast('Existe um PIX pendente para este pedido', 'warning');
                            abrirModalPix([resp], ctx.id);
                        }
                        else {gerarPix($modal, ctx.id, formasGateway);}
                    }).fail(function () {
                        gerarPix($modal, ctx.id, formasGateway);
                    });
                    return; // 🚨 ESSENCIAL → impede faturar junto
                }
                // 🔥 SÓ FATURA SE NÃO TEM PIX
                if (formasNormais.length > 0) {faturarNormal($modal, ctx.id, formasNormais, parcelas);}
            }
            if (ctx.tipo === 'caixa') {
                iniciarLoading();
                let formasNormais = [];
                let formasGateway = [];
                $modal.find('.table-formas tbody tr').each(function () {
                    const gateway = $(this).data('gateway');
                    const valor = parseBR($(this).data('valor') || 0);
                    if (valor <= 0) return;
                    const obj = {forma_id:$(this).data('forma'),valor:valor,parcelas:parseInt($(this).data('parcelas') || 1),dias:parseInt($(this).data('dias') || 0)};
                    if (gateway && gateway !== 'nenhum') {formasGateway.push(obj); }
                    else {formasNormais.push(obj);}
                });
                // 🔥 TEM PIX → NÃO FINALIZA AINDA
                if (formasGateway.length > 0) {
                    fetch('/lancpdvs/caixa/gerar-pagamento/', {
                        method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},body: JSON.stringify({formas: formasGateway})
                    }).then(r => r.json()).then(resp => {
                        if (resp.pagamentos && resp.pagamentos.length > 0) {
                            window._caixaPagamentoPendente = {formasNormais, formasGateway, parcelas};
                            const modalPix = abrirModalPix(resp.pagamentos, 0);
                            monitorarPagamentoCaixa(modalPix);
                        }
                        else {toast(`Erro ao gerar PIX!`, "error");}
                    });
                    return;
                }
                const totalPedido = getTotalPedido($modal);
                const totalPago = getTotalFormas($modal);
                let troco = 0;
                let permiteTroco = false;
                $modal.find('.table-formas tbody tr').each(function () {
                    const trocoAttr = $(this).attr('data-troco'); // 🔥 mais confiável
                    if (trocoAttr == "1") {permiteTroco = true;}
                });
                if (totalPago < totalPedido) {
                    toast(`Valor Pago é menor que o total!`, "warning");
                    return;
                }
                if (totalPago > totalPedido) {
                    if (!permiteTroco) {
                        toast(`Nenhuma forma permite troco!`, "warning");
                        return;
                    }
                    troco = totalPago - totalPedido;
                }
                // UI
                if (troco > 0) {
                    $modal.find('.troco-container').removeClass('d-none');
                    $modal.find('.troco').val(formatBR(troco));
                }
                else {$modal.find('.troco-container').addClass('d-none');}
                // 🔥 SEM PIX → FINALIZA DIRETO
                finalizarVendaCompleta(formasNormais, parcelas);
                limparTabelaFormas($modal);
                setTimeout(() => {
                    $("#id_cod_produtoCaixa").focus();
                }, 500);
                fecharLoading();
            }
        });
    });
    function faturarNormal($modal, pedidoId, formas, parcelas) {
        iniciarLoading();
        $.post(`/pedidos/faturar/${pedidoId}/`, {
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(), dados_pagamento: JSON.stringify(formas), parcelas_json: JSON.stringify(parcelas)
        }, function (resp) {
            if (resp.ok) {
                toast(`${resp.msg}`, "success");
                bootstrap.Modal.getInstance($modal[0])?.hide();
                // 🔥 recarrega página
                setTimeout(() => {
                    window.location.href = `/pedidos/lista/?s=${pedidoId}`;
                }, 3000);
            } else {
                toast(`${resp.msg || 'Erro ao faturar'}`, "warning");
                fecharLoading();
            }
        });
    }
    function gerarPix($modal, pedidoId, formas) {
        iniciarLoading();
        $.post(`/pedidos/${pedidoId}/gerar-pagamento/`, {
            csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(),
            formas: JSON.stringify(formas)
        }, function (resp) {
            fecharLoading();
            // Se o backend responder sucesso mas a lista vier vazia por causa de algum 'try/except' silencioso
            if (resp.pagamentos && resp.pagamentos.length > 0) {
                abrirModalPix(resp.pagamentos, pedidoId);
            } else {
                const msgErro = resp.erro || "Verifique as configurações do gateway.";
                toast(`Erro: ${msgErro}`, "error");
            }
        }).fail(function (xhr) {
            fecharLoading();
            let mensagemOriginal = "Erro de comunicação com o servidor.";
            try {
                // Tenta pegar a mensagem amigável enviada em JSON pelo Django
                const respostaJson = JSON.parse(xhr.responseText);
                if (respostaJson.erro) {
                    mensagemOriginal = respostaJson.erro;
                }
            } catch (e) {
                // Se o Django capotou e retornou uma tela amarela de erro (HTML), pega o texto do status
                mensagemOriginal = `Erro interno no servidor (${xhr.status}).`;
            }
            toast(`${mensagemOriginal}`, "error");
        });
    }
    function abrirModalPix(pagamentos, pedidoId) {
        let html = '';
        pagamentos.forEach(p => {
            const valorFormatado = formatBR(p.valor);
            const imgSrc = p.qr_base64.startsWith("data:") ? p.qr_base64 : `data:image/png;base64,${p.qr_base64}`;
            html += `
                <div class="mb-3">
                    <img src="${imgSrc}" width="220" class="mb-2">
                    <div class="input-group">
                        <input type="text" class="form-control text-center" value="${p.qr_code}" readonly>
                        <button class="btn btn-outline-secondary btn-copiar" data-code="${p.qr_code}"><i class="fa-regular fa-copy"></i></button>
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
        return modalPix;
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
                            <div class="check-circle mx-auto"><i class="fa-solid fa-check"></i></div>
                            <h5 class="text-success fw-bold">Pagamento confirmado!</h5>
                            <p class="text-muted mb-0">Finalizando Venda...</p>
                        </div>
                    `;
                    toast(`Pedido faturado com sucesso!`, "success");
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
    function monitorarPagamentoCaixa(modalPix) {
        const interval = setInterval(() => {
            $.get(`/lancpdvs/caixa/status-pagamento/`, function (resp) {
                if (resp.status === 'pago') {
                    clearInterval(interval);
                    const body = document.querySelector('#modalPixPagamento .modal-body');
                    body.innerHTML = `
                        <div class="text-center py-4">
                            <div class="check-circle mx-auto"><i class="fa-solid fa-check"></i></div>
                            <h5 class="text-success fw-bold">Pagamento confirmado!</h5>
                            <p class="text-muted mb-0">Finalizando Venda...</p>
                        </div>
                    `;
                    toast(`Pagamento confirmado! Finalizando venda...`, "success");
                    // 🔥 USA OS DADOS SALVOS (ESSENCIAL)
                    const dados = window._caixaPagamentoPendente;
                    if (dados) {
                        const todasFormas = [...dados.formasNormais, ...dados.formasGateway
                        ];
                        finalizarVendaCompleta(todasFormas, dados.parcelas);
                        // 🔥 limpa depois de usar
                        window._caixaPagamentoPendente = null;
                    }
                    setTimeout(() => {
                        modalPix.hide();
                        $('.modal-pagamento').modal('hide');
                    }, 1500);
                }
            });
        }, 3000);
    }
    function restaurarPadraoFilial() {
        const filial = DADOS_FILIAL[String(FILIAL_ID)];
        if (!filial) return;
        cliente = filial.cli ? {id: filial.cli, nome: filial.cli_nome} : null;
        vendedor = filial.vend ? {id: filial.vend, nome: filial.vend_nome} : null;
        tabelaPreco = filial.tb_preco ? {id: filial.tb_preco, nome: filial.tb_preco_nome} : null;
        AGRUPA_ITENS = !!filial.agrupa_itens;
        atualizarResumoVenda();
    }
    function finalizarVendaCompleta(formas, parcelas) {
        // 🔥 Pega o código do pedido original salvo no input oculto do caixa
        let codigoPedidoOrigem = $('#id_input_codigo_pedido_origem_oculto').val() || null;
        fetch('/lancpdvs/caixa/finalizar/', {
            method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCSRFToken()},
            body: JSON.stringify({
                caixa_id: CAIXA_ID, itens: itens, pagamentos: formas, cliente_id: cliente?.id, vendedor_id: vendedor?.id, tabela_preco_id: tabelaPreco?.id, codigo_pedido_origem: codigoPedidoOrigem // 🔥 ADICIONADO AQUI
            })
        }).then(r => r.json()).then(resp => {
            if (resp.sucesso) {
                let url = `/pedidos/cupom/${resp.pedido_id}/`;
                window.open(url, '_blank');
                toast(`Venda finalizada! Pedido ${resp.pedido_id}!`, "success");
                $("#num_pedido").val(resp.pedido_id);
                restaurarPadraoFilial();
                window._caixaPagamentoPendente = null;
                // 🔥 LIMPA O INPUT OCULTO após o sucesso para não contaminar a próxima venda normal
                $('#id_input_codigo_pedido_origem_oculto').val('');
                cancelarVenda();
                $('.modal-pagamento').modal('hide');
                $("#id_cod_produtoCaixa").focus();
            }
            else {toast(`${resp.erro}`, "error");}
        });
    }
    $('#imp_cupom').on('click', function () {
        let id = $('#num_pedido').val();
        if (!id) {
            toast(`Informe o número do pedido!`, "warning");
            return;
        }
        let url = `/pedidos/cupom/${id}/`;
        window.open(url, '_blank');
    });
    $('#imp_a4').on('click', function () {
        let id = $('#num_pedido').val();
        if (!id) {
            toast(`Informe o número do pedido!`, "warning");
            return;
        }
        let url = `/pedidos/a4/${id}/`;
        window.open(url, '_blank');
    });
    $('#mdReimprimir').on('shown.bs.modal', function () {$("#num_pedido").focus();});
    $('#modalTrocaDevolucao').on('shown.bs.modal', function () {$("#inputCodigoPedido").focus();});
    $("#inputCodigoPedido").on("keydown", function(event) {
    // Verifica se a tecla pressionada foi o Enter
        if (event.which === 13 || event.keyCode === 13) {
            event.preventDefault(); // Evita que a página recarregue se estiver dentro de um <form>
            let codigo = $(this).val().trim();
            if (codigo) {$("#btnBuscarPedidoTroca").click();}
            else {
                toast("Código do Pedido é necessário!", "warning");
                return;
            }
        }
    });
    const msg = sessionStorage.getItem('msg_sucesso');
    if (msg) {
        toast(`${msg}`, "success");
        sessionStorage.removeItem('msg_sucesso');
    }
    $(document).on('click', '.btn-abrir-modal-cancelamento', function () {
        const id = $(this).data('orcamento-id');
        const motivo = $(`#motivoCancelamento${id}`).val().trim();
        const modalTarget = $(this).data('bs-target');
        if (!motivo) {
            toast(`Informe o motivo do cancelamento!`, "warning");
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
            toast(`Informe o motivo do cancelamento!`, "warning");
            return;
        }
        $.ajax({
            url: `/orcamentos/canc.orc/${id}/`, type: 'POST', data: {motivo: motivo,  csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').first().val()}, success: function () {
                toast(`Orçamento cancelado com sucesso!`, "success");
                iniciarLoading();
                setTimeout(() => location.reload(), 3000);
            },
            error: function () {toast(`Erro ao cancelar orçamento!`, "error");}
        });
    });
    // Pedidos
    $(document).on('click', '.btn-abrir-modal-pedido', function () {
        const id = $(this).data('orcamento-id');
        const motivo = $(`#motivoCancelamento${id}`).val().trim();
        const modalTarget = $(this).data('bs-target');
        if (!motivo) {
            toast(`Informe o motivo do pedido!`, "warning");
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
            toast(`Informe o motivo do pedido!`, "warning");
            return;
        }
        $.ajax({
            url: `/pedidos/cancelar/${id}/`, type: 'POST', data: {motivo: motivo,  csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').first().val()}, success: function () {
                toast(`Pedido cancelado com sucesso!`, "success");
                iniciarLoading();
                setTimeout(() => location.reload(), 3000);
            },
            error: function () {toast(`Erro ao cancelar pedido!`, "error");}
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
            url: "/ajax/verificar-parcelas/", type: "GET", data: {parcelas: parcelas}, success: function(data){
                if(!data.permitido){
                    toast(`Quantidade de parcelas superior ao Permitido na Filial! Máximo: ${data.maximo} parcelas.`, "default");
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
                    toast(`Quantidade de dias superior ao Permitido na Filial! Máximo: ${data.maximo} dias.`, "default");
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
    $(document).on('blur', '[id^=parcelasPgto-], .parcelasPgto', function () {
        if (verificandoPedido) return;
        const $input = $(this);
        const parcelas = parseInt($input.val());
        if (!parcelas || parcelas <= 0) return;
        verificandoPedido = true;
        $.ajax({
            url: "/ajax/verificar-parcelas/", type: "GET", data: { parcelas: parcelas },
            success: function (data) {
                if (!data.permitido) {
                    toast(`Máximo permitido: ${data.maximo} parcelas.`, "default");
                    $input.val(data.maximo);
                    $input.focus();
                }
                verificandoPedido = false;
            },
            error: function () {verificandoPedido = false;}
        });
    });
    // DIAS
    $(document).on('blur', '[id^=diasPgto-], .diasPgto', function () {
        if (verificandoPedido) return;
        const $input = $(this);
        const dias = parseInt($input.val());
        if (!dias || dias <= 0) return;
        verificandoPedido = true;
        $.ajax({
            url: "/ajax/verificar-parcelas/", type: "GET", data: { dias: dias }, success: function (data) {
                if (!data.permitido) {
                    toast(`Máximo permitido: ${data.maximo} dias.`, "default");
                    $input.val(data.maximo);
                    $input.focus();
                }
                verificandoPedido = false;
            },
            error: function () {verificandoPedido = false;}
        });
    });
    // Teste
    if ($('#id_desconto, #id_acrescimo, #total-frete') === "") {$('#id_desconto, #id_acrescimo, #total-frete').val("0,00");}
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
    function parseDecimalAlt(v) {return parseBR(v);}
    function atualizarAltCorte($campoAlt) {
        const porta = $campoAlt.data('porta');
        const alt = parseDecimalAlt($campoAlt.val());
        const altCorte = (Math.round(alt * 100) + 5) / 100;
        $(`.alt-corte[data-porta="${porta}"]`).val(formatBR(altCorte));
        console.log('ALT FINAL:', formatBR(alt), 'ALT CORTE:', formatBR(altCorte));
    }
    function iniciarLoading() {
        $('#loadingOverlay').prop('hidden', false);
        requestAnimationFrame(() => {
            $('#loadingOverlay').addClass('show');
        });
    }
    let loadingTimeout = null;
    function fecharLoading() {
        $('#loadingOverlay').removeClass('show');
        setTimeout(() => {
            $('#loadingOverlay').prop('hidden', true);
        }, 250);
    }
    function arredondarComAjuste(valor) {
        let arredondado = parseBR(valor);
        let decimal = arredondado % 1;
        if (decimal >= 0.480 && decimal < 0.495) {arredondado = Math.floor(arredondado) + 0.50;}
        return formatBR(arredondado);
    }
    function arredondarInteiro(valor) {
        let num = parseBR(valor);
        if (isNaN(num)) return "";
        let inteiro = Math.floor(num);            // parte inteira
        let decimal = num - inteiro;              // parte decimal
        if (decimal > 0.50) {return inteiro + 1;}
        else {return inteiro;}
    }
    function calcFtPeso(porta) {
        let alt_corte = parseBR($(`.alt-corte[data-porta="${porta}"]`).val());
        let m2 = parseBR($(`.m2[data-porta="${porta}"]`).val()) || 0;
        if (isNaN(alt_corte)) {
            $(`.ft-peso[data-porta="${porta}"]`).val('');
            return;
        }
        let filialId = $('#id_vinc_fil').val();
        let multi = DADOS_FILIAL?.[filialId]?.multi_m2;
        if (!multi) multi = 15;
        let resultado = m2 * parseBR(multi);
        $(`.ft-peso[data-porta="${porta}"]`).val(formatBR(resultado));
    }
    function calcLgCorte(porta) {
        let largRaw = $(`.larg[data-porta="${porta}"]`).val();
        if (!largRaw) return "";
        let larg = parseBR(largRaw);
        if (isNaN(larg)) return "";
        const tp_vao = $(`.tipo-vao[data-porta="${porta}"]`).val();
        let calc = 0;
        let filialId = $('#id_vinc_fil').val();
        let multi1 = DADOS_FILIAL?.[filialId]?.multi_lg_corte1;
        let multi2 = DADOS_FILIAL?.[filialId]?.multi_lg_corte2;
        let multi3 = DADOS_FILIAL?.[filialId]?.multi_lg_corte3;
        if (tp_vao === "Fora do Vão") {calc = larg + parseBR(multi1);}
        else if (tp_vao === "Dentro do Vão") {calc = larg - parseBR(multi2);}
        else if (tp_vao === '1 Lado Dentro do Vão') {calc = larg + parseBR(multi3);}
        $(`.larg-corte[data-porta="${porta}"]`).val(formatBR(calc));
    }
    function calcPeso(porta) {
        let alt_corte = parseBR($(`.alt-corte[data-porta="${porta}"]`).val());
        let m2 = parseBR($(`.m2[data-porta="${porta}"]`).val()) || 0;
        if (isNaN(alt_corte)) {
            $(`.ft-peso[data-porta="${porta}"]`).val('');
            return;
        }
        let filialId = $('#id_vinc_fil').val();
        let multi = DADOS_FILIAL?.[filialId]?.multi_m2;
        if (!multi) multi = 15;
        let resultado = m2 * parseBR(multi);
        $(`.peso[data-porta="${porta}"]`).val(formatBR(resultado));
    }
    function calcTesteira(porta) {
        let peso = parseBR($(`.peso[data-porta="${porta}"]`).val()) || 0;
        let resultado = 0;
        if (peso <= 150) {resultado = 32;}
        else if (peso > 150 && peso <= 350) {resultado = 36;}
        else if (peso > 350 && peso <= 550) {resultado = 42;}
        else if (peso > 550 && peso <= 750) {resultado = 45;}
        else if (peso > 750) {resultado = 50;}
        $(`.testeira[data-porta="${porta}"]`).val(formatBR(resultado));
    }
    function calcM2(porta) {
        let larg_corte = parseBR($(`.larg-corte[data-porta="${porta}"]`).val()) || 0;
        let alt_corte  = parseBR($(`.alt-corte[data-porta="${porta}"]`).val()) || 0;
        let rolo       = parseBR($(`.rolo[data-porta="${porta}"]`).val()) || 0;
        let calc = (rolo + alt_corte) * larg_corte;
        let aux = arredondarComAjuste(calc);
        $(`.m2[data-porta="${porta}"]`).val(formatBR(aux));
    }
    function calcQtdLam(porta) {
        const filialId = $('#id_vinc_fil').val();
        let formula = DADOS_FILIAL?.[filialId]?.mt_qt_lam;
        if (!formula) return;
        const vars = {
            larg: parseBR($(`.larg[data-porta="${porta}"]`).val()) || 0, alt: parseBR($(`.alt[data-porta="${porta}"]`).val()) || 0, larg_corte: parseBR($(`.larg-corte[data-porta="${porta}"]`).val()) || 0,
            alt_corte: parseBR($(`.alt-corte[data-porta="${porta}"]`).val()) || 0, qtd_laminas: parseBR($(`.qtd-laminas[data-porta="${porta}"]`).val()) || 0,
            m2: parseBR($(`.m2[data-porta="${porta}"]`).val()) || 0, ft_peso: parseBR($(`.ft-peso[data-porta="${porta}"]`).val()) || 0,
            peso: parseBR($(`.peso[data-porta="${porta}"]`).val()) || 0, eix_mot: parseBR($(`.eix-mot[data-porta="${porta}"]`).val()) || 0, rolo: parseBR($(`.rolo[data-porta="${porta}"]`).val()) || 0,
        };
        // Substitui as variáveis pelos valores
        Object.entries(vars).forEach(([nome, valor]) => {
            formula = formula.replace(new RegExp(`\\b${nome}\\b`, 'g'), valor);
        });
        let resultado = 0;
        try {resultado = Function(`"use strict"; return (${formula});`)();}
        catch (e) {
            console.error("Erro na fórmula:", formula, e);
            return;
        }
        $(`.qtd-laminas[data-porta="${porta}"]`).val(arredondarInteiro(resultado));
    }
    function resetarControleRegras() {motorCtrl = {};}
    toastErrorShown = false;
    $(document).on("change", ".tipo-lamina", async function () {
        iniciarLoading();
        const porta = $(this).data("porta");
        await carregarProdutosIniciais(porta);
        await atualizarSubtotal();
        fecharLoading();
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
            await carregarProdutosIniciais(porta); // ← ela cuida de tudo
            await new Promise(resolve => setTimeout(resolve, 100));
            recalcularTotaisPorta(porta);
        }
        atualizarJSONPortas();
        gerarJSONFormas();
        atualizarSubtotal();
        fecharLoading();
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
                    $(`#tblAdc_${porta} .item-lista[data-item-id="${item.id}"]`).remove();
                    return false;
                }
                return true;
            });
            await carregarProdutosIniciais(porta);
        }
        await atualizarSubtotal();
        fecharLoading();
    });
    $(document).on("blur", ".alt", async function () {
        const idTabela = $('#id_tabela_preco').val();
        if (!idTabela) {
            toast(`Selecione a Tabela de Preço antes de gerar portas!`, "warning");
            $(this).val('');
            return;
        }
        const porta = $(this).data("porta");
        const lg = parseBR($(`.larg[data-porta="${porta}"]`).val()) || 0;
        const at = parseBR($(`.alt[data-porta="${porta}"]`).val()) || 0;
        if (lg <= 0 || at <= 0) return;
        medidasCtrl[porta] ??= {};
        const ctrl = medidasCtrl[porta];
        if (ctrl.larg === lg && ctrl.alt === at) { atualizarSubtotal(); return; }
        ctrl.larg = lg;
        ctrl.alt  = at;
        iniciarLoading();
        await carregarProdutosIniciais(porta); // ← ela cuida de tudo
        atualizarSubtotal();
        calcularValorForma();
        somaFormas();
        fecharLoading();
    });
    function calcularCamposDerivados(contexto) {
        const qtd_lam   = parseBR(contexto.qtd_lam) || 0;
        const larg_c    = parseBR(contexto.larg_c)  || 0;
        const alt_c     = parseBR(contexto.alt_c)   || 0;
        // 2. Pares de trava-lâminas
        const qtd_pares_trava = Math.ceil(qtd_lam / 2);
        // 3. Tamanho de corte por material (em metros)
        const corte_guia      = +formatBR((alt_c + 0.05));  // já vem de GUIAS_ALTURA
        const corte_eixo      = +formatBR(larg_c);           // já vem de EIXO_PESO
        const corte_soleira   = +formatBR(larg_c);           // já vem de SOLEIRA_LARGURA
        const corte_tubo      = +formatBR((alt_c + 0.20));   // já vem de TUBO_PESO
        const corte_perfil    = +formatBR((alt_c + 0.10));   // já vem de PERFIL_DESLIZANTE
        return {...contexto, qtd_pares_trava, corte_guia, corte_eixo, corte_soleira, corte_tubo, corte_perfil,};
    }
    // 1️⃣ NOVA FUNÇÃO: Carregar produtos pela primeira vez (baseado em regras)
    async function carregarProdutosIniciais(porta) {
        calcLgCorte(porta);
        // ✅ Calcula rolo em memória sem depender de produtos (só usa alt_c)
        const alt_c = parseBR($(`.alt-corte[data-porta="${porta}"]`).val()) || 0;
        const H_cm  = alt_c * 100;
        let rolo_calculado;
        if      (H_cm <= 200) rolo_calculado = 0.30;
        else if (H_cm <= 250) rolo_calculado = 0.34;
        else if (H_cm <= 300) rolo_calculado = 0.38;
        else if (H_cm <= 350) rolo_calculado = 0.42;
        else if (H_cm <= 400) rolo_calculado = 0.46;
        else if (H_cm <= 450) rolo_calculado = 0.50;
        else if (H_cm <= 500) rolo_calculado = 0.54;
        else if (H_cm <= 600) rolo_calculado = 0.60;
        else                  rolo_calculado = 0.65;
        // ✅ Aplica rolo no DOM antes de calcular m2
        $(`.rolo[data-porta="${porta}"]`).val(formatBR(rolo_calculado.toFixed(4)));
        // ✅ Agora calcula m2 com rolo correto — UMA única vez
        calcM2(porta);
        calcFtPeso(porta);
        calcPeso(porta);
        calcQtdLam(porta);
        // ✅ Monta contexto com m2 já correto
        const contextoBase = {
            largura: getFloat(`.larg[data-porta="${porta}"]`), altura: getFloat(`.alt[data-porta="${porta}"]`), larg_c: getFloat(`.larg-corte[data-porta="${porta}"]`),
            alt_c: getFloat(`.alt-corte[data-porta="${porta}"]`), m2: getFloat(`.m2[data-porta="${porta}"]`), peso: getFloat(`.peso[data-porta="${porta}"]`),
            qtd_lam:getFloat(`.qtd-laminas[data-porta="${porta}"]`),ft_peso:getFloat(`.ft-peso[data-porta="${porta}"]`),eix_mot:getFloat(`.eix-mot[data-porta="${porta}"]`),
            rolo: getFloat(`.rolo[data-porta="${porta}"]`), tipo_lamina: $(`.tipo-lamina[data-porta="${porta}"]`).val(), tipo_pintura: $('#id_tp_pintura').val(),
            tem_pintura: $('#id_pintura').val() === 'Sim',
        };
        const contexto = calcularCamposDerivados(contextoBase);
        const resp = await fetch(`${window.location.origin}/regras_produto/aplicar_regras_porta/`, {
            method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCSRFToken()},body:JSON.stringify({tabela_id:getTabelaPreco(),contexto: contexto})
        });
        if (!resp.ok) return;
        const data = await resp.json();
        if (!data.success) return;
        const derivados = data.campos_derivados || {};
        $(`.qtd-pares-trava[data-porta="${porta}"]`).val(derivados.qtd_pares_trava ?? '');
        if (derivados.tipo_eixo) $(`.tipo-eixo[data-porta="${porta}"]`).val(derivados.tipo_eixo);
        prodManager.data[porta] = (prodManager.data[porta] || []).filter(item => !item.regra_origem || item.qtd_manual);
        prodAdcManager.data[porta] = (prodAdcManager.data[porta] || []).filter(item => !item.regra_origem || item.qtd_manual);
        $(`#tblProd_${porta} .item-lista[data-regra-origem]`).not('[data-manual="true"]').remove();
        $(`#tblAdc_${porta} .item-lista[data-regra-origem]`).not('[data-manual="true"]').remove();
        data.produtos.forEach(it => {
            const ehAdicional = it.tp_prod === 'Adicional';
            const manager  = ehAdicional ? prodAdcManager : prodManager;
            const tabelaId = ehAdicional ? 'tblAdc' : 'tblProd';
            const modalId  = ehAdicional ? 'editItemAdcModal' : 'editItemModal';
            const novoProduto = {id:it.id,cod:it.codigo,desc:it.desc_prod,unid:it.unidProd,vl_compra:it.vl_compra,vl_unit:it.vl_unit,qtd_final:it.qtd,qtd_manual:false,
                regra_origem:it.regra_origem || null,tp_prod:it.tp_prod,ativo: true,especifico:it.especifico,espessura_lam:it.espessura_lam,peso_m2:it.peso_m2,
                diametro_eixo:it.diametro_eixo
            };
            manager.data[porta].push(novoProduto);
            $(`#${tabelaId}_${porta}`).append(montarTrProduto({porta, item: novoProduto, modalEditar: modalId, regraOrigem: novoProduto.regra_origem || ''}));
        });
        // ✅ Recalcula testeira apenas (rolo e m2 já estão corretos)
        calcTesteira(porta);
        recalcularTotaisPorta(porta);
    }
    // 2️⃣ FUNÇÃO ATUAL: Recalcular qtd de produtos JÁ EXISTENTES
    async function atualizarTabelaPorta(porta) {
        const ctrl = medidasCtrl[porta] || {};
        const larg   = Number(ctrl.larg)   || 0;
        const alt    = Number(ctrl.alt)    || 0;
        const larg_c = parseBR($(`.larg-corte[data-porta="${porta}"]`).val()) || 0;
        const alt_c  = parseBR($(`.alt-corte[data-porta="${porta}"]`).val()) || 0;
        const m2     = parseBR($(`.m2[data-porta="${porta}"]`).val()) || 0;
        const eix_mot = parseBR($(`.eix-mot[data-porta="${porta}"]`).val()) || 0;
        const qtd_lam = parseBR($(`.qtd-laminas[data-porta="${porta}"]`).val()) || 0;
        const ft_peso = parseBR($(`.ft-peso[data-porta="${porta}"]`).val()) || 0;
        const peso   = parseBR($(`.peso[data-porta="${porta}"]`).val()) || 0;
        const rolo   = parseBR($(`.rolo[data-porta="${porta}"]`).val()) || 0;
        const contextoBase = {alt,alt_c,larg,larg_c,m2,peso,qtd_lam,rolo,ft_peso,eix_mot,tipo_lamina:$(`.tipo-lamina[data-porta="${porta}"]`).val(),
            tipo_pintura:$('#id_tp_pintura').val(),tem_pintura:$('#id_pintura').val() === 'Sim',
        };
        const contexto = calcularCamposDerivados(contextoBase);
        const produtos = [];
        const idsAdicionados = new Set();
        const linhasProd = $(`#tblProd_${porta} .item-lista`).length;
        const linhasAdc  = $(`#tblAdc_${porta} .item-lista`).length;
        if (linhasProd === 0 && linhasAdc === 0) return;
        function adicionarProduto($tr) {
            const id = Number($tr.data('item-id'));
            if (!id || idsAdicionados.has(id)) return;
            idsAdicionados.add(id);
            const qtdManual = $tr.data('qtd-manual');
            let qtd = (qtdManual !== undefined && qtdManual !== null) ? Number(qtdManual) : (parseBR($tr.find('.qtd-div').text()) || 0);
            produtos.push({id: id, qtd: qtd});
        }
        $(`#tblProd_${porta} .item-lista`).each(function () { adicionarProduto($(this)); });
        $(`#tblAdc_${porta} .item-lista`).each(function () { adicionarProduto($(this)); });
        if (produtos.length === 0) return;
        const resp = await fetch('/regras_produto/calcular_orcamento/', {
            method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':getCSRFToken()},body:JSON.stringify({tabela_id:getTabelaPreco(),contexto:contexto,produtos:produtos})
        });
        const data = await resp.json();
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
        $(`#tblProd_${porta} .item-lista`).each(function () {
            const $tr = $(this);
            const id = Number($tr.data('item-id'));
            const origem = $tr.data('regra-origem');
            if (!origem) return;
            const qtdManual = $tr.data('qtd-manual');
            let qtdExibida = null;
            if (qtdManual !== undefined && qtdManual !== null) {qtdExibida = parseBR(qtdManual) || 0;}
            else {
                const txt = $tr.find('.qtd-div').text();
                qtdExibida = txt ? parseBR(txt) : 0;
            }
            if (qtdExibida > 0) {return;}
            if (!idsRetornados.has(id)) {$tr.hide();}
        });
        $(`#tblAdc_${porta} .item-lista`).each(function () {
            const $tr = $(this);
            const id = Number($tr.data('item-id'));
            const origem = $tr.data('regra-origem');
            if (!origem) return;
            const qtdManual = $tr.data('qtd-manual');
            let qtdExibida = null;
            if (qtdManual !== undefined && qtdManual !== null) {qtdExibida = parseBR(qtdManual) || 0;}
            else {
                const txt = $tr.find('.qtd-div').text();
                qtdExibida = txt ? parseBR(txt) : 0;
            }
            if (qtdExibida > 0) {return;}
            if (!idsRetornados.has(id)) {$tr.hide();}
        });
        data.itens.forEach(item => {
            let $tr = $(`#tblProd_${porta} .item-lista[data-item-id="${item.id}"]`);
            let tipo = 'prod';
            if (!$tr.length) {
                $tr = $(`#tblAdc_${porta} .item-lista[data-item-id="${item.id}"]`);
                tipo = 'adc';
            }
            if (!$tr.length) return;
            let qtdManual = $tr.data('qtd-manual');
            let qtdBackend = Number(item.qtd) || 0;
            let qtd;
            if (qtdManual !== undefined && qtdManual !== null && qtdManual > 0) {qtd = Number(qtdManual);}
            else {qtd = qtdBackend;}
            if ($tr.data('regra-origem') && qtd <= 0) {
                $tr.hide();
                return;
            }
            $tr.show();
            const vlCompra = parseBR($tr.find('.vl-c-div').text());
            const vlUnit   = parseBR($tr.find('.vl-u-div').text());
            const totCompra = isFinite(vlCompra * qtd) ? vlCompra * qtd : 0;
            const totVenda  = isFinite(vlUnit * qtd) ? vlUnit * qtd : 0;
            $tr.find('.qtd-div').text(formatBR(qtd));
            $tr.find('.tot-c-div').text(formatBR(totCompra));
            $tr.find('.tot-v-div').text(formatBR(totVenda));
            atualizarQtdNoManager(porta, item.id, qtd);
            if (tipo === 'prod') {
                totalCompraProd += totCompra;
                totalVendaProd  += totVenda;
            } else {
                totalCompraAdc += totCompra;
                totalVendaAdc  += totVenda;
            }
        });
        $(`#totCompra_porta_${porta}`).text("R$ " + formatBR(totalCompraProd));
        $(`#totVenda_porta_${porta}`).text("R$ " + formatBR(totalVendaProd));
        $(`#totCompraAdc_porta_${porta}`).text("R$ " + formatBR(totalCompraAdc));
        $(`#totVendaAdc_porta_${porta}`).text("R$ " + formatBR(totalVendaAdc));
    }
    gerarJSONFormas();
    let debounceTimeout;
    function atualizarCalculoCompletoDebounced() {
        clearTimeout(debounceTimeout);
        debounceTimeout = setTimeout(() => {calcFtPeso();}, 200);
    }
    $('#id_alt, #id_tp_vao, #id_larg, #id_qtd, #id_rolo, #id_alt_corte, #id_larg_corte').on('blur', atualizarCalculoCompletoDebounced);
    $(document).on('input', '.money, #editQtdInput, #editQtdAdcInput, #id_qtd_prod, #id_qtd_prod_adc, #id_vl_compra, #id_vl_prod, #id_vl_prod_adc, .editable, .inpFrete, #id_desconto, #id_acrescimo, #desconto, #acrescimo', function() {
        formatBR(this);
    });
    $(document).on('blur', '.money, #editQtdInput, #editQtdAdcInput, #id_qtd_prod, #id_qtd_prod_adc, #id_vl_compra, #id_vl_prod, #id_vl_prod_adc, .editable, .inpFrete, #id_desconto, #id_acrescimo, #desconto, #acrescimo', function() {
        const num = parseBR($(this).val());
        $(this).val(formatInputBR(num));
    });
    var desconto = 0;
    var total = 0;
    function atualizarSubtotal() {
        return new Promise(resolve => {
            let subtotal   = 0;
            let custoTotal = 0;
            let vl_p_s = parseBR($('#id_vl_p_s').val());
            $('[id^="tblProd_"] .item-lista, [id^="tblAdc_"] .item-lista').each(function () {
                const compraTxt = $(this).find('.tot-c-div').text().trim();
                const vendaTxt  = $(this).find('.tot-v-div').text().trim();
                const compra = parseBR(compraTxt);
                const venda  = parseBR(vendaTxt);
                custoTotal += compra;
                subtotal   += venda;
            });
            subtotal += vl_p_s;
            $('#custoTotal_txt').text('R$ ' + formatBR(custoTotal));
            $('#subtotal_txt').text('R$ ' + formatBR(subtotal));
            $('#id_vl_form_pgto').val(aplicarMascaraMoney(subtotal));
            const descontoRaw = $('#id_desconto').length ? $('#id_desconto').val() : '0';
            const acrescimoRaw = $('#id_acrescimo').length ? $('#id_acrescimo').val() : '0';
            const desconto  = parseBR(descontoRaw);
            const acrescimo = parseBR(acrescimoRaw);
            const total = parseBR(subtotal - desconto + acrescimo);
            $('#desconto').text('R$ ' + formatBR(desconto));
            $('#acrescimo').text('R$ ' + formatBR(acrescimo));
            $('#total_txt').text('R$ ' + formatBR(total));
            const margemLucro = subtotal > 0 ? ((subtotal - custoTotal) / subtotal) * 100 : 0;
            $('#margem_txt').text(formatBR(margemLucro) + '%');
            calcularValorForma();
            somaFormas();
            resolve();
        });
    }
    atualizarSubtotal();
    function calcularValorForma() {
        const totalValor = parseBR($('#total_txt').text());
        let totalPago = 0;
        $('.tb-formas-orc-lista .item-lista').each(function() {
            const valor = parseBR($(this).find('.vl-orc-div').text());
            totalPago += valor;
        });
        let restante = totalValor - totalPago;
        restante = Math.max(0, Math.round(restante * 100) / 100);
        $('#id_vl_form_pgto').val(formatBR(restante));
    }
    function verificarTotalFormas() {
        const totalValor = parseBR($('#total_txt').text());
        let totalFormas = 0;
        $('.tb-formas-orc-lista .item-lista').each(function () {totalFormas += parseBR($(this).find('.vl-orc-div').text());});
        const totalArred = parseBR(totalValor);
        const formasArred = parseBR(totalFormas);
        $("#somaFormas").text(formatBR(formasArred));
        if (Math.abs(totalArred - formasArred) > 0.01) {
            $('#form_pgtoBtn').click();  // exibe modal de erro, se necessário
            return false;
        }
        return true;
    }
    function somaFormas() {
        let soma = 0;
        const linhas = $('.tb-formas-orc-lista .item-lista').filter(function () {return $(this).find('div').length > 0;});
        if (linhas.length === 0) {
            $("#somaFormas").text("R$ 0,00");
            return true;
        }
        linhas.each(function () {
            const valor = parseBR($(this).find('.vl-orc-div').text());
            soma += valor;
        });
        const total = parseBR(soma);
        $("#somaFormas").text("R$ " + formatBR(total));
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
            toast(`Informe uma quantidade válida de Portas!`, "warning");
            return;
        }
        if (window.prodManager?.data) prodManager.data = {};
        if (window.prodAdcManager?.data) prodAdcManager.data = {};
        resetarControleRegras();
        $(".tb-portas-lista .item-lista").empty();
        $("#accordionProdutos").empty();
        $("#accordionAdicionais").empty();
        for (let i = 1; i <= qtd; i++) {
            $(".tb-portas-lista").append(`
                <div>
                    <small class="badge rounded-pill text-bg-dark num-porta ms-1 mt-1">Porta #${i}</small>
                    <!-- Ações -->
                    <div class="col-md-1 mb-1 mb-md-1 mt-1 acoes-col" style="float: right;">
                        <div class="btn-group btn-group-sm">
                            <button type="button" class="btn btn-light btn-sm border btn-detalhes-porta" data-porta="${i}" data-bs-toggle="modal" data-bs-target="#modalDetalhePorta" title="Detalhes da porta"><i class="fa-solid fa-gear"></i></button>
                            <button type="button" class="btn btn-light btn-sm border removerPorta" data-porta="${i}"><i class="fa-solid fa-trash-can text-danger"></i></button>
                        </div>
                    </div>
                </div>
                <div class="list-group-item py-1 item-lista linha-porta" id="linha_resumo_${i}" data-porta="${i}">
                    <div class="row align-items-center linha-lista">
                        <div class="col-md-1 fw-semibold">
                            <!-- Largura -->
                            <div class="border-bottom codigo-col lg-div" data-label="Largura:">
                                <small class="f-flex d-md-none">Largura:</small><input type="text" class="form-control form-control-sm border-dark-subtle larg" name="larg" data-porta="${i}" placeholder="0,00">
                            </div>
                            <!-- Altura -->
                            <div class="border-bottom codigo-col at-div" data-label="Altura:">
                                <small class="f-flex d-md-none">Altura:</small><input type="text" class="form-control form-control-sm border-dark-subtle alt" name="alt" data-porta="${i}" placeholder="0,00">
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Largura de Corte -->
                            <div class="border-bottom codigo-col lg-c-div" data-label="Lg. Corte:">
                                <small class="f-flex d-md-none">Lg. Corte:</small><input readonly class="form-control form-control-sm border-dark-subtle larg-corte" name="larg-corte" data-porta="${i}" placeholder="0,00">
                            </div>
                            <!-- Altura de Corte -->
                            <div class="border-bottom codigo-col at-c-div" data-label="At. Corte:">
                                <small class="f-flex d-md-none">At. Corte:</small><input readonly class="form-control form-control-sm border-dark-subtle alt-corte" name="alt-corte" data-porta="${i}" placeholder="0,00">
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Quantidade de Lâminas -->
                            <div class="border-bottom codigo-col qtd-l-div" data-label="Qtd. Lâm.:">
                                <small class="f-flex d-md-none">Qtd. Lâm.:</small><input readonly class="form-control form-control-sm border-dark-subtle qtd-laminas" name="qtd-laminas" data-porta="${i}" placeholder="0,00">
                            </div>
                            <!-- M² -->
                            <div class="border-bottom codigo-col m2-div" data-label="M²:">
                                <small class="f-flex d-md-none">M²:</small><input readonly class="form-control form-control-sm border-dark-subtle m2" name="m2" data-porta="${i}" placeholder="0,00">
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Fator Peso -->
                            <div class="border-bottom codigo-col ft-p-div" data-label="Ft. Peso:">
                                <small class="f-flex d-md-none">Ft. Peso:</small><input readonly class="form-control form-control-sm border-dark-subtle ft-peso" name="ft-peso" data-porta="${i}" placeholder="0,00">
                            </div>
                            <!-- Peso -->
                            <div class="border-bottom codigo-col peso-div" data-label="Peso:">
                                <small class="f-flex d-md-none">Peso:</small><input readonly class="form-control form-control-sm border-dark-subtle peso" name="peso" data-porta="${i}" placeholder="0,00">
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Rolo -->
                            <div class="border-bottom codigo-col rolo-div" data-label="Rolo:">
                                <small class="f-flex d-md-none">Rolo:</small><input readonly class="form-control form-control-sm border-dark-subtle rolo" name="rolo" data-porta="${i}" placeholder="0,00">
                            </div>
                            <!-- Tipo Lâmina -->
                            <div class="border-bottom codigo-col tp-l-div" data-label="Tipo Lâmina:">
                                <small class="f-flex d-md-none">Tipo Lâmina:</small>
                                <select class="form-select form-select-sm border-dark-subtle tipo-lamina" name="tipo-lamina" data-porta="${i}">
                                    <option value="FECHADA_24">Lisa Fechada - Chapa 24 (1.20cm)</option>
                                    <option value="FECHADA_22">Lisa Fechada - Chapa 22 (1.30cm)</option>
                                    <option value="FECHADA_20">Lisa Fechada - Chapa 20 (1.40cm)</option>
                                    <option value="TRANSVISION_24">Transvision - Chapa 24 (1.20cm)</option>
                                    <option value="TRANSVISION_22">Transvision - Chapa 22 (1.30cm)</option>
                                    <option value="TRANSVISION_20">Transvision - Chapa 20 (1.40cm)</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Guia Esquerdo -->
                            <div class="border-bottom codigo-col g-e-div" data-label="Guia Esquerdo:">
                                <small class="f-flex d-md-none">Guia Esquerdo:</small>
                                <select class="form-select form-select-sm border-dark-subtle guia-esq" name="guia-esq" data-porta="${i}">
                                    <option value="Dentro do Vão">Dentro do Vão</option>
                                    <option value="Fora do Vão">Fora do Vão</option>
                                </select>
                            </div>
                            <!-- Guia Direito -->
                            <div class="border-bottom codigo-col g-d-div" data-label="Guia Direito:">
                                <small class="f-flex d-md-none">Guia Direito:</small>
                                <select class="form-select form-select-sm border-dark-subtle guia-dir" name="guia-dir" data-porta="${i}">
                                    <option value="Dentro do Vão">Dentro do Vão</option>
                                    <option value="Fora do Vão">Fora do Vão</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-2 fw-semibold">
                            <!-- Tipo Vão -->
                            <div class="border-bottom codigo-col tp-v-div" data-label="Tipo Vão:">
                                <small class="f-flex d-md-none">Tipo Vão:</small>
                                <select class="form-select form-select-sm border-dark-subtle tipo-vao" name="tipo-vao" data-porta="${i}">
                                    <option value="Fora do Vão">Fora do Vão</option>
                                    <option value="Dentro do Vão">Dentro do Vão</option>
                                    <option value="1 Lado Dentro do Vão">1 Lado Dentro do Vão</option>
                                </select>
                            </div>
                            <!-- Acabamento Guia -->
                            <div class="border-bottom codigo-col ac-g-div" data-label="Acabamento Guia:">
                                <small class="f-flex d-md-none">Acabamento Guia:</small>
                                <select class="form-select form-select-sm border-dark-subtle acab-guia" name="acab-guia" data-porta="${i}">
                                    <option value="Sem Acabamento">Sem Acabamento</option>
                                    <option value="Com Acabamento">Com Acabamento</option>
                                    <option value="Acabamento Especial">Acabamento Especial</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Tipo Acionamento -->
                            <div class="border-bottom codigo-col tp-ac-div" data-label="Tipo Acionamento:">
                                <small class="f-flex d-md-none">Tipo Acionamento:</small>
                                <select class="form-select form-select-sm border-dark-subtle tipo-acio" name="tipo-acio" data-porta="${i}">
                                    <option value="Manual">Manual</option>
                                    <option value="Elétrico">Elétrico</option>
                                    <option value="Elétrico c/ Botoeira">Elétrico c/ Botoeira</option>
                                    <option value="Automático">Automático</option>
                                </select>
                            </div>
                            <!-- Lado Motor -->
                            <div class="border-bottom codigo-col ld-mot-div" data-label="Lado Motor:">
                                <small class="f-flex d-md-none">Lado Motor:</small>
                                <select class="form-select form-select-sm border-dark-subtle lado-motor" name="lado-motor" data-porta="${i}">
                                    <option value="Esquerdo">Esquerdo</option>
                                    <option value="Direito">Direito</option>
                                    <option value="Central">Central</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Tipo Mola -->
                            <div class="border-bottom codigo-col tp-ml-div" data-label="Tipo de Mola:">
                                <small class="f-flex d-md-none">Tipo de Mola:</small>
                                <select class="form-select form-select-sm border-dark-subtle tipo-mola" name="tipo-mola" data-porta="${i}">
                                    <option value="Sem Mola">Sem Mola</option>
                                    <option value="Mola Simples">Mola Simples</option>
                                    <option value="Mola Dupla">Mola Dupla</option>
                                </select>
                            </div>
                            <!-- Tipo Travamento -->
                            <div class="border-bottom codigo-col tp-trav-div" data-label="Tipo Travamento:">
                                <small class="f-flex d-md-none">Tipo Travamento:</small>
                                <select class="form-select form-select-sm border-dark-subtle tipo-travamento" name="tipo-travamento" data-porta="${i}">
                                    <option value="Sem Trava">Sem Trava</option>
                                    <option value="Trava Manual">Trava Manual</option>
                                    <option value="Trava Elétrica">Trava Elétrica</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Posição do Eixo -->
                            <div class="border-bottom codigo-col pos-eixo-div" data-label="Posição Eixo:">
                                <small class="f-flex d-md-none">Posição Eixo:</small>
                                <select class="form-select form-select-sm border-dark-subtle posicao-eixo" name="posicao-eixo" data-porta="${i}">
                                    <option value="Escondido">Escondido</option>
                                    <option value="Aparente">Aparente</option>
                                </select>
                            </div>
                            <!-- Tipo Instalação -->
                            <div class="border-bottom codigo-col tp-inst-div" data-label="Tipo Instalação:">
                                <small class="f-flex d-md-none">Tipo Instalação:</small>
                                <select class="form-select form-select-sm border-dark-subtle tipo-instalacao" name="tipo-instalacao" data-porta="${i}">
                                    <option value="Atrás do Vão">Atrás do Vão</option>
                                    <option value="Dentro do Vão">Dentro do Vão</option>
                                    <option value="Fora do Vão">Fora do Vão</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-1 fw-semibold">
                            <!-- Testeira -->
                            <div class="border-bottom codigo-col testeira-div" data-label="Testeira (cm):">
                                <small class="f-flex d-md-none">Testeira (cm):</small>
                                <input readonly class="form-control form-control-sm border-dark-subtle testeira" name="testeira" data-porta="${i}" placeholder="0,00">
                            </div>
                            <!-- Qtd Pares Trava -->
                            <div class="border-bottom codigo-col qtd-pares-div" data-label="Pares Trava:">
                                <small class="f-flex d-md-none">Pares Trava:</small>
                                <input readonly class="form-control form-control-sm border-dark-subtle qtd-pares-trava" name="qtd-pares-trava" data-porta="${i}" placeholder="0">
                            </div>
                        </div>
                    </div>
                </div>
            `);
            $("#accordionProdutos").append(criarAcordeonProdutos(i));
            $("#accordionAdicionais").append(criarAcordeonAdicionais(i));
            recalcularTotaisPorta(i);
        }
    }
    // Abre o modal e carrega os dados da porta
    $(document).on('click', '.btn-detalhes-porta', function () {
        pintarOptions();
        const porta = $(this).data('porta');
        $('#modalPortaId').val(porta);
        $('#modalPortaNumero').text(porta);
        renderFotosPorta(porta);
        const d = portaDetalhes[porta] || {};
        $('#det_pintura_porta').val(d.pintura_porta ?? 'Sim');
        $('#det_cor_porta').val(d.cor_porta ?? '');
        $('#det_nr_serie_motor').val(d.nr_serie_motor ?? '');
        $('#det_garantia_motor_meses').val(d.garantia_motor_meses ?? '12');
        $('#det_possui_passagem').val(d.possui_passagem_pedestre ? 'true' : 'false');
        $('#det_largura_passagem').val(d.largura_passagem ?? '');
        $('#det_altura_passagem').val(d.altura_passagem ?? '');
        $('#det_obs_porta').val(d.obs_porta ?? '');
        togglePassagem($('#det_possui_passagem').val());
    });
    // Mostra/esconde campos de passagem pedestre
    function togglePassagem(val) {
        const show = val === 'true';
        $('#det_grupo_passagem, #det_grupo_altura_passagem').toggle(show);
    }
    $('#det_possui_passagem').on('change', function () {togglePassagem($(this).val());});
    // Salva no objeto portaDetalhes em memória
    $('#btnSalvarDetalhesPorta').on('click', function () {
        const porta = $('#modalPortaId').val();
        if (!portaFotos[porta])
            portaFotos[porta] = [];
        portaDetalhes[porta] = {
            pintura_porta: $('#det_pintura_porta').val(), cor_porta: $('#det_cor_porta').val(), nr_serie_motor: $('#det_nr_serie_motor').val(),
            garantia_motor_meses: $('#det_garantia_motor_meses').val() || null, possui_passagem_pedestre: $('#det_possui_passagem').val() === 'true',
            largura_passagem: $('#det_largura_passagem').val() || 0, altura_passagem: $('#det_altura_passagem').val() || 0, obs_porta: $('#det_obs_porta').val(),
        };
        atualizarJSONPortas();
        bootstrap.Modal.getInstance(document.getElementById('modalDetalhePorta')).hide();
    });
    $(document).on('focus', '.id_larg, .larg-corte, .testeira, .alt-corte, .qtd-laminas, .m2, .ft-peso, .qtd-prod-adc, .qtd-prod, .valor-prod, .valor-prod-adc', function () {
        if (!$(this).data('mask-applied')) {formatBR($(this));}
    });
    function inicializarCamposDecimais() {
        const CAMPOS = '.larg, .alt';
        $(CAMPOS).each(function () {
            if (!$(this).val()) {$(this).val('0,00');}
            else {$(this).val(formatInputBR($(this).val()));}
        });
    }
    const CAMPOS_DECIMAIS = '.larg, .alt';
    // evita duplicar evento
    $(document).off('focus.decimal').on('focus.decimal', CAMPOS_DECIMAIS, function () {
        let val = $(this).val();
        if (!val || val === '0,00') {$(this).data('raw', '');}
        else {$(this).data('raw', parseBR(val) * 100);}
        this.select();
    });
    $(document).off('input.decimal').on('input.decimal', CAMPOS_DECIMAIS, function () {
        let valor = $(this).val();
        let raw = valor.replace(/\D/g, '');
        $(this).data('raw', raw);
        if (!raw) {
            $(this).val('0,00');
            if ($(this).hasClass('alt')) {atualizarAltCorte($(this));}
            return;
        }
        let num = parseInt(raw, 10) / 100;
        $(this).val(formatInputBR(num));
        if ($(this).hasClass('alt')) {atualizarAltCorte($(this));}
    });
    $(document).off('blur.decimal').on('blur.decimal', CAMPOS_DECIMAIS, function () {
        let val = $(this).val();
        if (!val || val === '') {$(this).val('0,00');}
        else {$(this).val(formatInputBR(val));}
        if ($(this).hasClass('alt')) {atualizarAltCorte($(this));}
    });
    $(document).on('change', '.guia-esq, .guia-dir', function() {console.log("ALTEROU GUIA:", $(this).val(), "PORTA:", $(this).data('porta'));});
    function criarFormularioProduto(num) {
        return `
            <div class="row g-2 mb-3 form-produto" data-porta="${num}">
                <div class="col-md-2">
                    <label name="cod-prod" class="form-label">Cód. Produto</label>
                    <div class="input-group">
                        <input type="text" class="form-control form-control-sm cod-prod" data-porta="${num}" name="cod-prod" placeholder="Cód. Produto">
                        <button class="btn btn-outline-dark btn-sm btn-busca-prod" type="button" data-porta="${num}" data-bs-toggle="modal" data-bs-target="#produtoModal"><i class="fa-solid fa-magnifying-glass"></i></button>
                    </div>
                </div>
                <div class="col-md-3">
                    <label name="desc-prod" class="form-label">Descrição</label>
                    <input type="text" class="form-control form-control-sm desc-prod" data-porta="${num}" name="desc-prod" disabled>
                </div>
                <div class="col-md-1">
                    <label name="unid-prod" class="form-label">Unidade</label>
                    <input type="text" class="form-control form-control-sm unid-prod" data-porta="${num}" name="unid-prod" disabled>
                </div>
                <div class="col-md-2">
                    <label name="valor-prod" class="form-label">Valor</label>
                    <input type="text" class="form-control form-control-sm valor-prod text-end" name="valor-prod" value="0,00" style='color: darksuccess; font-weight: bold; background: honeydew;' data-porta="${num}">
                </div>
                <div class="col-md-2">
                    <label name="qtd-prod" class="form-label">Qtde.</label>
                    <input type="text" class="form-control form-control-sm qtd-prod" name="qtd-prod" placeholder="0,00" value="0,00" data-porta="${num}">
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
                        <div class="list-group tb-prod-orc-lista" id="tblProd_${num}">
                            <!-- Cabeçalho -->
                            <div class="list-group-item bg-light fw-bold cabecalho-lista">
                                <div class="row align-items-center">
                                    <div class="col-md-1 border-end">Código</div>
                                    <div class="col-md-4 border-end">Descrição</div>
                                    <div class="col-md-1 border-end">Unidade</div>
                                    <div class="col-md-1 text-center border-end">Valor Custo</div>
                                    <div class="col-md-1 text-center border-end">Valor Venda</div>
                                    <div class="col-md-1 text-center border-end">Quantidade</div>
                                    <div class="col-md-1 border-end">Total Custo</div>
                                    <div class="col-md-1 border-end">Total Venda</div>
                                    <div class="col-md-1">Ações</div>
                                </div>
                            </div>
                        </div>
                        <div class="d-flex justify-content-end gap-4 mt-2 porta-totais" data-porta="${num}">
                            <span>
                                <strong>Total Custo:</strong>
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
                    <label for="cod-prod-adc" class="form-label">Cód. Produto</label>
                    <div class="input-group">
                        <input type="text" class="form-control form-control-sm cod-prod-adc" name="cod-prod-adc" data-porta="${num}" placeholder="Cód. Produto">
                        <button class="btn btn-outline-dark btn-sm btn-busca-prod-adc" type="button" data-porta="${num}" data-bs-toggle="modal" data-bs-target="#produtoAdcModal"><i class="fa-solid fa-magnifying-glass"></i></button>
                    </div>
                </div>
                <div class="col-md-2">
                    <label for="desc-prod-adc" class="form-label">Descrição</label>
                    <input type="text" class="form-control form-control-sm desc-prod-adc" name="desc-prod-adc" data-porta="${num}" disabled>
                </div>
                <div class="col-md-1">
                    <label for="unid-prod-adc" class="form-label">Unidade</label>
                    <input type="text" class="form-control form-control-sm unid-prod-adc" name="unid-prod-adc" data-porta="${num}" disabled>
                </div>
                <input type="hidden" class="vl-compra-prod-adc" data-porta="${num}" value="0,00">
                <div class="col-md-2">
                    <label for="valor-prod-adc" class="form-label">Valor</label>
                    <input type="text" class="form-control form-control-sm valor-prod-adc text-end" name="valor-prod-adc" value="0,00" style='color: darksuccess; font-weight: bold; background: honeydew;' data-porta="${num}">
                </div>
                <div class="col-md-1">
                    <label for="qtd-prod-adc" class="form-label">Qtde.</label>
                    <input type="text" class="form-control form-control-sm qtd-prod-adc" placeholder="0,00" value="0,00" name="qtd-prod-adc" data-porta="${num}">
                </div>
                <div class="col-md-2 mt-2 campo-lado-adc d-none">
                    <label for="lado-adc" class="form-label">Lado</label>
                    <select class="form-select form-select-sm lado-adc" name="lado-adc" data-porta="${num}">
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
                        <div class="list-group tb-adc-orc-lista" id="tblAdc_${num}">
                            <!-- Cabeçalho -->
                            <div class="list-group-item bg-light fw-bold cabecalho-lista">
                                <div class="row align-items-center">
                                    <div class="col-md-1 border-end">Código</div>
                                    <div class="col-md-4 border-end">Descrição</div>
                                    <div class="col-md-1 border-end">Unidade</div>
                                    <div class="col-md-1 text-center border-end">Valor Custo</div>
                                    <div class="col-md-1 text-center border-end">Valor Venda</div>
                                    <div class="col-md-1 text-center border-end">Quantidade</div>
                                    <div class="col-md-1 border-end">Total Custo</div>
                                    <div class="col-md-1 border-end">Total Venda</div>
                                    <div class="col-md-1">Ações</div>
                                </div>
                            </div>
                        </div>
                        <div class="d-flex justify-content-end gap-4 mt-2 porta-totais" data-porta="${num}">
                            <span>
                                <strong>Total Custo:</strong>
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
            item = {id: Number(dados.cod), cod: Number(dados.cod), desc: dados.desc || '', unid: dados.unid || '', vl_compra: parseBR(dados.vl_compra) || 0, vl_unit: parseBR(dados.vl) || 0,
                qtd_calc: 0, qtd_final: 0, qtd_manual: true, ativo: true, ...extra
            };
            manager.data[p].push(item);
        }
        item.desc = dados.desc || item.desc;
        item.unid = dados.unid || item.unid;
        item.qtd_final = parseBR(dados.qtd) || 0;
        item.qtd_manual = true;
        item.ativo = item.qtd_final > 0;
        item.vl_unit = parseBR(dados.vl) || 0;
        item.vl_compra = parseBR(dados.vl_compra) || parseBR(item.vl_compra) || 0;
        Object.assign(item, extra);
        const totCompra = item.qtd_final * item.vl_compra;
        const vlTotal = item.qtd_final * item.vl_unit;
        item.tot_compra = totCompra;
        item.vl_total = vlTotal;
        let $row = $(`#${tabelaId}_${p} .item-lista[data-item-id="${item.cod}"]`);
        if (!$row.length) {
            $row = $(montarTrProduto({porta: p, item, modalEditar: tabelaId === 'tblAdc' ? 'editItemAdcModal' : 'editItemModal'}));
            $(`#${tabelaId}_${p}`).append($row); // ← era `#${tabelaId}_${p} .item-lista`
        }
        atualizarLinha($row, item);
        atualizarTabelaPorta(p);
        atualizarSubtotal();
        atualizarJSONPortas();
    }
    function atualizarLinha($row, item) {
        const f = v => formatBR(v || 0);
        $row.find('.desc-div').text(item.desc);
        $row.find('.unid-div').text(item.unid);
        $row.find('.vl-c-div').text(f(item.vl_compra));
        $row.find('.vl-u-div').text(f(item.vl_unit));
        $row.find('.qtd-div').text(f(item.qtd_final));
        $row.find('.tot-c-div').text(f(item.tot_compra));
        $row.find('.tot-v-div').text(f(item.vl_total));
    }
    function adicionarProdutoNaTabela(porta, dados) {adicionarItemTabela({manager: prodManager, tabelaId: 'tblProd', porta, dados});}
    function adicionarAdicionalNaTabela(porta, dados) {adicionarItemTabela({manager: prodAdcManager, tabelaId: 'tblAdc', porta, dados, extra: {lado: dados.lado || '', especifico: dados.especifico || ''}});}
    $(document).on("click", ".btn-add-prod", function () {
        const porta = $(this).data("porta");
        const cod  = $(`.cod-prod[data-porta="${porta}"]`).val();
        const desc = $(`.desc-prod[data-porta="${porta}"]`).val();
        const unid = $(`.unid-prod[data-porta="${porta}"]`).val();
        const qtd  = parseBR($(`.qtd-prod[data-porta="${porta}"]`).val()) || 0;
        const vl   = parseBR($(`.valor-prod[data-porta="${porta}"]`).val()) || 0;
        if (!cod || !desc || qtd <= 0) {
            toast(`Produto principal incompleto!`, "warning");
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
        const qtd  = parseBR($(`.qtd-prod-adc[data-porta="${porta}"]`).val()) || 0;
        const vl   = parseBR($(`.valor-prod-adc[data-porta="${porta}"]`).val()) || 0;
        const vl_compra_raw = $form.find('.vl-compra-prod-adc').val();
        const vl_compra = parseBR(vl_compra_raw) || 0;
        const lado = $(`.lado-adc[data-porta="${porta}"]`).val() || '';
        const especifico = ($form.data('especifico') || '').trim();
        console.log('ADD ADC', { cod, desc, unid, qtd, vl, vl_compra, vl_compra_raw });
        const precisaLado = ['Portinhola', 'Alçapão', 'Coluna Removível'].includes(especifico);
        if (!cod || !desc || qtd <= 0) {
            toast(`Produto adicional incompleto!`, "warning");
            return;
        }
        if (precisaLado && !lado) {
            toast(`Selecione o lado do produto adicional!`, "warning");
            $(`.lado-adc[data-porta="${porta}"]`).focus();
            return;
        }
        adicionarAdicionalNaTabela(porta, {cod, desc, unid, qtd, vl, vl_compra, lado, especifico});
        $(`.cod-prod-adc[data-porta="${porta}"], .desc-prod-adc[data-porta="${porta}"], .unid-prod-adc[data-porta="${porta}"], .valor-prod-adc[data-porta="${porta}"], .qtd-prod-adc[data-porta="${porta}"]`).val('');
        $form.find('.vl-compra-prod-adc').val('0,00');
        $(`.lado-adc[data-porta="${porta}"]`).val('');
        $form.removeData('especifico');
        $form.find('.campo-lado-adc').addClass('d-none');
        $(`.cod-prod-adc[data-porta="${porta}"]`).focus();
    });
    function observarTotaisPorta(porta) {
        const tabela = document.querySelector("#tblProd_" + porta + " .item-lista");
        if (!tabela) return;
        const observer = new MutationObserver(() => {recalcularTotaisPorta(porta);});
        observer.observe(tabela, {childList: true, subtree: true, characterData: true});
        const tabelaAdc = document.querySelector("#tblAdc_" + porta + " .item-lista");
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
        $("#tblProd_" + porta + " .item-lista").each(function () {
            const compra = parseBR($(this).find(".tot-c-div").text());
            const venda  = parseBR($(this).find(".tot-v-div").text());
            totalCompra += compra;
            totalVenda += venda;
        });
        $("#tblAdc_" + porta + " .item-lista").each(function () {
            const compra = parseBR($(this).find(".tot-c-div").text());
            const venda  = parseBR($(this).find(".tot-v-div").text());
            totalCompraAdc += compra;
            totalVendaAdc += venda;
        });
        $("#totCompra_porta_" + porta).text(formatBR(totalCompra));
        $("#totVenda_porta_" + porta).text(formatBR(totalVenda));
        $("#totCompraAdc_porta_" + porta).text(formatBR(totalCompraAdc));
        $("#totVendaAdc_porta_" + porta).text(formatBR(totalVendaAdc));
    }
    $(".porta-totais").each(function () {
        const porta = $(this).data("porta");
        recalcularTotaisPorta(porta);
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
        const $tr   = $(this).closest('.item-lista'); // ✅
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
        $(`#tblProd_${porta} .item-lista`).empty();
        $(`#tblAdc_${porta} .item-lista`).empty();
    }
    function reindexarPortas() {
        let novoIndice = 1;
        $(".tb-portas-lista .item-lista").each(function () {
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
            $(this).find(".tb-prod-orc-lista").attr("id", "tblProd_" + novoIndice);
            novoIndice++;
        });
        novoIndice = 1;
        $("#accordionAdicionais .acc-adicional").each(function () {
            $(this).attr("id", "accAdc_" + novoIndice);
            $(this).attr("data-porta", novoIndice);
            $(this).find(".accordion-header").attr("id", "headingAdc_" + novoIndice);
            $(this).find(".accordion-button").attr("data-bs-target", "#collapseAdc_" + novoIndice).text("Adicionais – Porta " + novoIndice);
            $(this).find(".accordion-collapse").attr("id", "collapseAdc_" + novoIndice);
            $(this).find(".tb-adc-orc-lista").attr("id", "tblAdc_" + novoIndice);
            novoIndice++;
        });
        $("#qtd_portas").val($(".tb-portas-lista .item-lista").length);
        if (typeof atualizarJSONPortas === "function") {atualizarJSONPortas();}
    }
    function getCSRFToken() {return document.cookie.split('; ').find(row => row.startsWith('csrftoken=')) ?.split('=')[1];}
    // Espessura por tipo de lâmina (cm)
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
    function hidratarFotos(portas) {
        portaFotos = {};
        portas.forEach(function(porta) {
            const p = porta.numero;
            if (!p) return;
            portaFotos[p] = (porta.fotos || []).map(function(f) {
                return {id: f.id, url: f.url, principal: f.principal, ordem: f.ordem, novo: false};
            });
        });
    }
    function hidratarDetalhes(portas) {
        portaDetalhes = {};
        portas.forEach(function(porta) {
            const p = porta.numero;
            if (!p) return;
            portaDetalhes[p] = {
                pintura_porta: porta.pintura_porta ?? 'Sim', cor_porta: porta.cor_porta ?? '', nr_serie_motor: porta.nr_serie_motor ?? '',
                garantia_motor_meses: porta.garantia_motor_meses ?? '', possui_passagem_pedestre: porta.possui_passagem_pedestre ?? false,
                largura_passagem: porta.largura_passagem ?? 0, altura_passagem: porta.altura_passagem ?? 0, obs_porta: porta.obs_porta ?? '',
            };
        });
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
        $('div[id^="tblProd_"]').each(function () {
            const p = this.id.split('_')[1];
            const produtos = (prodManager.data[p] || []).filter(i => i.ativo && i.qtd_final > 0).map(i => ({
                codProd: i.cod, qtdProd: i.qtd_final, vl_unit: i.vl_unit, vl_total: i.qtd_final * i.vl_unit, ativo: true, regra_origem: i.regra_origem || ''
            }));
            const adicionais = (prodAdcManager.data[p] || []).filter(i => i.ativo && i.qtd_final > 0).map(i => ({
                codProd: i.cod, qtdProd: i.qtd_final, vl_unit: i.vl_unit, vl_total: i.qtd_final * i.vl_unit, ativo: true, lado: i.lado || '', regra_origem: i.regra_origem || ''
            }));
            const det = portaDetalhes[p] || {};
            portas.push({
                // Campos originais
                numero: Number(p), produtos, adicionais, largura: getFloat(`.larg[data-porta="${p}"]`), altura: getFloat(`.alt[data-porta="${p}"]`),
                qtd_lam: getFloat(`.qtd-laminas[data-porta="${p}"]`), m2: getFloat(`.m2[data-porta="${p}"]`), larg_corte: getFloat(`.larg-corte[data-porta="${p}"]`),
                alt_corte: getFloat(`.alt-corte[data-porta="${p}"]`), rolo: getFloat(`.rolo[data-porta="${p}"]`), peso: getFloat(`.peso[data-porta="${p}"]`),
                ft_peso: getFloat(`.ft-peso[data-porta="${p}"]`), eix_mot: getFloat(`.eix-mot[data-porta="${p}"]`), tipo_lamina: $(`.tipo-lamina[data-porta="${p}"]`).val() || '',
                tipo_vao: $(`.tipo-vao[data-porta="${p}"]`).val() || '', op_guia_e: $(`.guia-esq[data-porta="${p}"]`).val() || '', op_guia_d: $(`.guia-dir[data-porta="${p}"]`).val() || '',
                // Campos novos da grade
                acabamento_guia: $(`.acab-guia[data-porta="${p}"]`).val() || '', tp_acionamento: $(`.tipo-acio[data-porta="${p}"]`).val() || '',
                lado_motor: $(`.lado-motor[data-porta="${p}"]`).val() || '', tp_mola: $(`.tipo-mola[data-porta="${p}"]`).val() || '', tp_travamento: $(`.tipo-travamento[data-porta="${p}"]`).val() || '',
                posicao_eixo: $(`.posicao-eixo[data-porta="${p}"]`).val() || '', tp_instalacao: $(`.tipo-instalacao[data-porta="${p}"]`).val() || '',
                testeira: getFloat(`.testeira[data-porta="${p}"]`) || null, qtd_pares_trava: getFloat(`.qtd-pares-trava[data-porta="${p}"]`) || 0,
                // Campos do modal de detalhes
                pintura_porta: det.pintura_porta ?? 'Sim', cor_porta: det.cor_porta ?? '', nr_serie_motor: det.nr_serie_motor ?? '',
                garantia_motor_meses: det.garantia_motor_meses ?? null, possui_passagem_pedestre: det.possui_passagem_pedestre ?? false,
                largura_passagem: det.largura_passagem ?? 0, altura_passagem: det.altura_passagem ?? 0, obs_porta: det.obs_porta ?? '',
                // foto_vao é enviada separado via FormData — não entra no JSON
            });
        });
        $('#id_json_portas').val(JSON.stringify(portas));
        return true;
    }
    // Listeners — dispara atualização ao mudar qualquer campo da grade
    $(document).on('change',
        '.guia-esq, .guia-dir, .tipo-vao, .acab-guia, .tipo-acio, ' +
        '.lado-motor, .tipo-mola, .tipo-travamento, .posicao-eixo, ' +
        '.tipo-instalacao, .tipo-lamina',
        function () { atualizarJSONPortas(); }
    );
    function getFloat(selector) {
        const el = $(selector);
        if (!el.length) return 0;
        const val = el.val();
        if (!val) return 0;
        return parseBR(val) || 0;
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
        const est_min = $("#id_estoque_minimo").val();
        const est_max = $("#id_estoque_maximo").val();
        //Para Entrada de Pedidos/NF
        const fornecedor = getSelect2IdIfExists('#id_fornecedor');
        const tipoPedido = $("#id_tipo").val();
        const numeracao = $("#id_numeracao").val();
        let campoInvalido = null;
        let nomeCampo = '';

        if (temPintura === "Sim" && (!corSelecionada || corSelecionada === "")) {
            toast(`Escolha uma cor da pintura antes de gravar!`, "warning");
            $("#medidasBtn").click();
            return false;
        }
        if (filial !== undefined && !filial) {
            toast(`Filial deve ser informada!`, "warning");
            $("#clienteBtn").click();
            return false;
        }
        if (fornecedor !== undefined && !fornecedor) {
            toast(`Fornecedor deve ser informado!`, "warning");
            $("#clienteBtn").click();
            return false;
        }
        if ((!numeracao || numeracao === "") && tipoPedido === "Pedido") {
            toast(`Numeração do Pedido deve ser informada!`, "warning");
            return false;
        } else if ((!numeracao || numeracao === "") && tipoPedido === "Nota Fiscal") {
            toast(`Numeração da Nota Fiscal deve ser informada!`, "warning");
            return false;
        }
        if (solicitante !== undefined && !solicitante) {
            toast(`Solicitante deve ser informado!`, "warning");
            $("#clienteBtn").click();
            return false;
        }
        if (cliente !== undefined && !cliente) {
            toast(`Cliente deve ser informado!`, "warning");
            $("#clienteBtn").click();
            return false;
        }
        if (est_min === "0,00" && est_max != "0,00") {
            toast(`Estoque máximo definido, Estoque mínimo também deve ser informado!`, "warning");
            return false;
        }
        if (est_min != "0,00" && est_max === "0,00") {
            toast(`Estoque mínimo definido, Estoque máximo também deve ser informado!`, "warning");
            return false;
        }
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
            toast(`${nomeCampo} deve ser preenchido!`, "warning");
            return false; // 🚨 ESSENCIAL
        }
        if (!verificarTotalFormas()) {
            toast(`Total das formas de pagamento não corresponde ao valor total!`, "warning");
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
        $('#id_vl_form_pgto').val('0,00');
    }
    $("#btnGerarPortas").on("click", function() {
        const selectData = $('#id_tabela_preco').select2('data');
        const tabelaPreco = selectData[0]?.id;
        if (!tabelaPreco) {
            toast(`Tabela de Preço deve ser informada!`, "warning");
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
    $(document).on("keydown", ".tb-portas-lista input", function(e) {
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
        const $tr = $(this).closest('.item-lista');
        const porta = Number($tr.data('porta'));
        const itemId = Number($tr.data('item-id'));
        const isProd = $tr.closest('[id^="tblProd_"]').length > 0; // ✅
        const isAdc  = $tr.closest('[id^="tblAdc_"]').length > 0;  // ✅
        if (isProd) {
            prodManager.setEditingItem($tr);
            console.log('DEBUG EDIT:', {porta, itemId, dataPorta: prodManager.data[porta]});
            const item = prodManager.data[porta]?.find(i => i.id === itemId);
            console.log('UNIDADE ITEM:', item);
            if (!item) return;
            $('#editItemModal .modal-title').html(`<i class="fa-solid fa-pen-to-square"></i> Editar Item ${item.cod}`);
            const cod  = item.cod ?? $tr.find('.cod-div').text().trim();
            const desc = item.desc ?? $tr.find('.desc-div').text().trim();
            const unid = item.unid ?? $tr.find('.unid-div').text().trim();
            const vl = item.vl_unit ?? item.vl_unitario ?? parseBR($tr.find('.vl-u-div').text()) ?? 0;
            const qtd = item.qtd_final ?? item.qtd ?? parseBR($tr.find('.qtd-div').text()) ?? 0;
            $('#editCódInput').val(cod);
            $('#editDescInput').val(desc);
            $('#editUnidInput').val(unid);
            $('#editValorItemInput').val(formatBR(vl));
            $('#editQtdInput').val(formatBR(qtd));
            const modalEdit = new bootstrap.Modal(document.getElementById('editItemModal'));
            modalEdit.show();
        }
        else if (isAdc) {
            prodAdcManager.setEditingItem($tr);
            const item = prodAdcManager.data[porta]?.find(i => i.id === itemId);
            if (!item) return;
            $('#editItemAdcModal .modal-title').html(`<i class="fa-solid fa-pen-to-square"></i> Editar Item ${item.cod}`);
            const cod  = item.cod ?? $tr.find('.cod-div').text().trim();
            const desc = item.desc ?? $tr.find('.desc-div').text().trim();
            const unid = item.unid ?? $tr.find('.unid-div').text().trim();
            const vl   = item.vl_unit ?? parseBR($tr.find('.vl-u-div').text()) ?? 0;
            const qtd  = item.qtd_final ?? parseBR($tr.find('.qtd-div').text()) ?? 0;
            const vlCompra = item.vl_compra ?? parseBR($tr.find('.vl-c-div').text()) ?? 0;
            $('#editCódAdcInput').val(cod);
            $('#editDescAdcInput').val(desc);
            $('#editUnidAdcInput').val(unid);
            $('#editValorItemAdcInput').val(formatBR(vl));
            $('#editQtdAdcInput').val(formatBR(qtd));
            $('#editValorCompraItemAdcInput').val(formatBR(vlCompra));
            const modalAdc = new bootstrap.Modal(document.getElementById('editItemAdcModal'));
            modalAdc.show();
        }
    });
    $('#saveEditBtn').on('click', function () {
        iniciarLoading();
        const { porta, itemId } = prodManager.currentEditing;
        if (!porta || !itemId) return;
        const cells = [$('#editCódInput').val().trim(), $('#editDescInput').val().trim(), $('#editUnidInput').val().trim(), $('#editValorItemInput').val().trim(), $('#editQtdInput').val().trim()];
        prodManager.updateEditingItem(cells);
        const $tr = $(`#tblProd_${porta} .item-lista[data-item-id="${itemId}"]`);
        const qtdManual = parseBR($('#editQtdInput').val()) || 0;
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
            atualizarJSONPortas();
        }, 500);
        fecharLoading();
    });
    $('#saveEditAdcBtn').on('click', function () {
        iniciarLoading();
        const { porta, itemId } = prodAdcManager.currentEditing;
        if (!porta || !itemId) return;
        const item = prodAdcManager.data[porta]?.find(i => i.id === itemId);
        if (!item) return;
        const cod = $('#editCódAdcInput').val().trim();
        const desc = $('#editDescAdcInput').val().trim();
        const unid = $('#editUnidAdcInput').val().trim();
        const vl = parseBR($('#editValorItemAdcInput').val()) || 0;
        const qtd = parseBR($('#editQtdAdcInput').val()) || 0;
        const vl_compra = parseBR($('#editValorCompraItemAdcInput').val()) || 0;
        adicionarAdicionalNaTabela(porta, {cod, desc, unid, qtd, vl, vl_compra, lado: item.lado || '', especifico: item.especifico || ''});
        const $tr = $(`#tblAdc_${porta} .item-lista[data-item-id="${itemId}"]`);
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
        }, 500);
        fecharLoading();
    });
    $('.remQtd').on('click', function () {
        let qtd = parseBR($('#editQtdInput').val()) || 0;
        if (qtd > 0) $('#editQtdInput').val(formatInputBR((qtd - 1)));
    });
    $('.addQtd').on('click', function () {
        let qtd = parseBR($('#editQtdInput').val()) || 0;
        $('#editQtdInput').val(formatInputBR((qtd + 1)));
    });
    $('.remQtdAdc').on('click', function () {
        let qtd = parseBR($('#editQtdAdcInput').val()) || 0;
        if (qtd > 0) $('#editQtdAdcInput').val(formatInputBR((qtd - 1)));
    });
    $('.addQtdAdc').on('click', function () {
        let qtd = parseBR($('#editQtdAdcInput').val()) || 0;
        $('#editQtdAdcInput').val(formatInputBR((qtd + 1)));
    });
    const formaManager = {
        addItem(cells, options = {}) {
            const idx = $('.tb-formas-orc-lista .item-lista').length + 1;
            const geraParcelas = options.geraParcelas == 1 || options.geraParcelas === true;
            const parcelasExibir = geraParcelas ? cells[2] : '-';
            const diasExibir     = geraParcelas ? cells[3] : '-';
            const parcelas = geraParcelas ? (cells[2] || 1) : 1;
            const dias     = geraParcelas ? (cells[3] || 0) : 0;
            $('.tb-formas-orc-lista').append(`
                <div class="list-group-item py-1 item-lista" data-forma-id="${options.formaId || ''}" data-valor="${options.valor || 0}" data-parcelas="${parcelas}" data-dias="${dias}" data-gera-parcelas="${geraParcelas ? 1 : 0}" data-troco="${options.troco ? 1 : 0}" data-gateway="${options.gateway || ''}" data-credencial='${JSON.stringify(options.credencial || {}).replace(/'/g, "&apos;")}'>
                    <div class="row align-items-center linha-lista">
                        <!-- Item da Forma -->
                        <div class="col-md-1 fw-bold descricao-col num-orc-div text-secondary" data-label="Item:">${idx}</div>
                        <!-- Forma de Pagamento -->
                        <div class="col-md-5 fw-semibold descricao-col forma-orc-div" data-label="Forma de Pagamento:">${cells[0]}</div>
                        <!-- Valor -->
                        <div class="col-md-2 fw-semibold codigo-col vl-orc-div text-success" data-label="Valor:">${cells[1]}</div>
                        <!-- Parcelas -->
                        <div class="col-md-2 text-center fw-semibold codigo-col parc-orc-div" data-label="Qtde. Parcelas:">${parcelasExibir}</div>
                        <!-- Dias -->
                        <div class="col-md-1 text-center fw-semibold codigo-col dias-orc-div" data-label="Qtde. Dias:">${diasExibir}</div>
                        <!-- Ações -->
                        <div class="col-md-1 text-center mb-1 mb-md-0 acoes-col">
                            <div class="btn-group btn-group-sm">
                                <button class="btn btn-light btn-sm border deleteFormaBtn"><i class="fa-solid fa-trash-can text-danger"></i></button>
                            </div>
                        </div>
                    </div>
                </div>
            `);
        }
    };
    function addForma(formaId, formaPgto, valor, parcelas = 1, dias = 0, gateway = '', geraParcelas = false, credenciais = {}, troco = false) {
        const valorNumero = parseBR(valor) || 0;
        const valorExibicao = formatBR(valorNumero);
        const parcelasExibicao = geraParcelas ? parcelas : '-';
        const diasExibicao     = geraParcelas ? dias : '-';
        // 🔥 AQUI ESTÁ A CORREÇÃO PRINCIPAL
        formaManager.addItem(
            [formaPgto, valorExibicao, parcelasExibicao, diasExibicao],
            {formaId: formaId, valor: valorNumero, parcelas: parcelas, dias: dias, gateway: gateway, geraParcelas: geraParcelas, credencial: credenciais, troco: troco}
        );
        atualizarSubtotal();
        verificarTotalFormas();
        calcularValorForma();
        somaFormas();
        gerarJSONFormas();
    }
    function gerarJSONFormas() {
        const formas = [];
        $('.tb-formas-orc-lista .item-lista').each(function (i) {
            const $row = $(this);
            const forma_id = $row.data('forma-id');
            // 🔥 CORREÇÃO AQUI
            let valorRaw = $row.data('valor');
            if (typeof valorRaw === 'string') {valorRaw = valorRaw.replace(/\./g, '');}
            const valor = parseBR(valorRaw) || 0;
            const gera_parcelas = !!$row.data('gera-parcelas');
            const parcelas = gera_parcelas ? ($row.data('parcelas') ?? 1) : 1;
            const dias     = gera_parcelas ? ($row.data('dias') ?? 0) : 0;
            const gateway  = ($row.data('gateway') || '').toString().toLowerCase();
            console.log(`Linha ${i + 1}`, {forma_id, valor, parcelas, dias, gateway, gera_parcelas});
            if (!forma_id || valor < 0.01) {
                console.warn(`Linha ${i + 1} ignorada`);
                return;
            }
            formas.push({forma_id, valor: parseBR(valor), parcelas, dias, gateway, gera_parcelas});
        });
        const json = JSON.stringify(formas);
        $('#id_json_formas_pgto').val(json);
        return formas;
    }
    $('#confirmBtn').on('click', function () {
        gerarJSONFormas();
        const modalElement = document.getElementById('staticBackdrop');
        const modalConfirm = bootstrap.Modal.getInstance(modalElement);
        if (modalConfirm) {modalConfirm.hide();}
        atualizarJSONPortas();
        const form = $("#createForm");
        // Remove inputs antigos caso exista um novo envio
        form.find(".input-foto-dinamico").remove();
        Object.entries(portaFotos).forEach(function ([porta, fotos]) {
            if (!fotos.length) return;
            // Cria um DataTransfer contendo todas as fotos da porta
            const dt = new DataTransfer();
            fotos.forEach(function (foto) {
                if (foto.novo)
                    dt.items.add(foto.file);
            });
            // Cria apenas UM input para a porta
            const input = document.createElement("input");
            input.type = "file";
            input.multiple = true;
            input.name = "fotos_" + porta;
            input.className = "input-foto-dinamico";
            input.style.display = "none";
            input.files = dt.files;
            console.log("Qtd arquivos:", dt.files.length);
            form.append(input);
            console.log(input.name);
            console.log(input.files.length);
        });
        iniciarLoading();
        console.log(portaFotos);
        console.log(form[0].elements);
        $("#id_fotos_remover").val(JSON.stringify(fotosRemover));
        form[0].submit();
    });
    function formaJaExiste(formaId) {
        let existe = false;
        $('.tb-formas-orc-lista .item-lista').each(function () {
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
        const valor    = parseBR(valorStr);
        const parcelas = parseInt($('#id_parcelas').val()) || 1;
        const dias     = parseInt($('#id_dias').val()) || 30;
        if (!formaPgto) {
            toast(`Forma de Pagamento deve ser informada!`, "warning");
            $("#form_pgtoBtn").click();
            return;
        }
        if (valor <= 0) {
            toast(`Informe um valor válido!`, "warning");
            return;
        }
        if (formaJaExiste(formaPgto)) {
            toast(`Forma de pagamento já inclusa na tabela!`, "warning");
            return;
        }
        $.ajax({
            url: `/formas_pgto/forma-pgto-info/${formaPgto}/`, method: "GET", success: function (response) {
                console.log(response);
                addForma(response.id, response.descricao, valor, parcelas, dias, response.gateway, response.gera_parcelas, response.credenciais, response.troco);
                $('#id_formas_pgto').val(null).trigger('change');
                // (opcional) limpa campos auxiliares
                $('#id_vl_form_pgto').val('');
                $('#id_parcelas').val(1);
                $('#id_dias').val(30);
            }
        });
    });
    $(document).on('click', '.deleteFormaBtn', function () {
        const row = $(this).closest('.item-lista'); // ✅ sobe até a linha certa
        row.remove();
        $('.tb-formas-orc-lista .item-lista').each(function(i){$(this).find('.num-orc-div').text(i + 1);});
        atualizarSubtotal();
        verificarTotalFormas();
        somaFormas();
        gerarJSONFormas();
    });
    $('#addItemProdBtn').on('click', function() {
        const codigo = $('#id_cod_prod').val().trim(); // Assumindo que você tem campos específicos para produtos adicionais
        const descricao = $('#id_desc_prod').val().trim();
        const unidade = $('#id_unidProd').val().trim();
        const valor = parseBR($('#id_vl_prod').val().trim());
        const quantidade = parseBR($('#id_qtd_prod').val().trim());
        if(!codigo || !descricao || !unidade || isNaN(valor) || isNaN(quantidade) || quantidade <= 0) {return toast(`Preencha todos os campos corretamente!`, "warning");}
        prodAdcManager.addItem([codigo, descricao, unidade, valor, valor, quantidade]);
        $('#id_cod_prod, #id_desc_prod, #id_unidProd, #id_vl_prod, #id_qtd_prod').val('');
        $('#id_cod_prod').focus();
    });
    $('#addItemProdAdcBtn').on('click', function() {
        const codigo = $('#id_cod_prod_adc').val().trim(); // Assumindo que você tem campos específicos para produtos adicionais
        const descricao = $('#id_desc_prod_adc').val().trim();
        const unidade = $('#id_unidProd_adc').val().trim();
        const valor = parseBR($('#id_vl_prod_adc').val().trim());
        const quantidade = parseBR($('#id_qtd_prod_adc').val().trim());
        if (!codigo || !descricao || !unidade || isNaN(valor) || isNaN(quantidade) || quantidade <= 0) {return toast(`Preencha todos os campos corretamente!`, "warning");}
        prodAdcManager.addItem([codigo, descricao, unidade, 0.00, valor, quantidade, 0.00, (valor * quantidade)]);
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
        const lg = parseBR(larg);
        const at = parseBR(alt);
        if (lg === lastLg && at === lastAt) {
            console.log("Click sem mudança — não resetando tabelas.");
            return;
        }
        $(`.larg[data-porta="${porta}"], .alt[data-porta="${porta}"]`).blur();
    });
    $('#id_cod_prod').on('blur keydown', function(event) {
        if (event.type === 'blur' || event.key === 'Enter') {
            const productId = $(this).val();
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
                        if (produto.vl_prod === "0,00" || produto.vl_prod === "") {$('#id_vl_prod').focus();}
                        else {$('#id_qtd_prod').focus();}
                    }
                    else {toast(`Código de produto não encontrado!`, "warning");}
                }, error: function() {toast(`Erro ao buscar o produto. Tente novamente!`, "error");}
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
                    toast(`Código de produto não encontrado!`, "warning");
                    return;
                }
                const produto = response.produtos[0];
                if (isAdicional) {$form.data('especifico', produto.especifico || '');}
                let map;
                if (isAdicional) {map = {desc: '.desc-prod-adc', unid: '.unid-prod-adc', valor: '.valor-prod-adc', qtd: '.qtd-prod-adc'};}
                else {map = {desc: '.desc-prod', unid: '.unid-prod', valor: '.valor-prod', qtd: '.qtd-prod'};}
                $form.find(map.desc).val(produto.desc_prod);
                $form.find(map.unid).val(produto.unidProd);
                $form.find(map.valor).val(formatBR(produto.vl_prod));
                if (isAdicional) {$form.find('.vl-compra-prod-adc').val(produto.vl_compra ? parseBR(produto.vl_compra) : '0,00');}
                const $qtd = $form.find(map.qtd);
                $qtd.val('1.00').data('auto', false);
                toggleCampoLado($form, produto, isAdicional);
                $form.find(map.valor).focus();
            },
            error() {toast(`Erro ao buscar o produto. Tente novamente!`, "error");}
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
                        $('#orc_cpfCnpj').val(cliente.cpfCnpj);
                        $('#orc_email').val(cliente.email);
                        $('#orc_tel').val(cliente.tel);
                        $('#orc_cep').val(cliente.cep);
                        $('#orc_endereco').val(cliente.endereco);
                        $('#orc_numero').val(cliente.numero);
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
        const alt_vlCaixa = $("#id_alt_vlEd").val();
        $('#id_preco_unitP').prop('disabled', alt_vl !== "Sim");
        $('#id_preco_unitEd').prop('disabled', alt_vlCaixa !== "Sim");
    }
    function atualizarLabel() {
        const tipo = ($("#id_tipo_desc_acres").val() || '').trim().toLowerCase();
        const tipoCaixa = ($("#id_tipo_desc_acresEd").val() || '').trim().toLowerCase();
        const operacao = ($("#id_atribuir").val() || '').trim().toLowerCase();
        const operacaoCaixa = ($("#id_atribuirEd").val() || '').trim().toLowerCase();
        const vl = parseBR($('#id_preco_unitP').val());
        const vlCaixa = parseBR($('#id_preco_unitEd').val());
        const qtd = parseBR($('#id_quantidadeP').val()) || 0;
        const qtdCaixa = parseBR($('#id_quantidadeEd').val()) || 0;
        const base = vl * qtd;
        const baseCaixa = vlCaixa * qtdCaixa;
        const valor = parseBR($('#id_desc_acres').val());
        const valorCaixa = parseBR($('#id_desc_acresEd').val());
        const $label = $("label[for='id_desc_acres']");
        const $labelCaixa = $("label[for='id_desc_acresEd']");
        let prefixo = operacao === "acréscimo" || operacao === "acrescimo" || operacaoCaixa === "acréscimo" || operacaoCaixa === "acrescimo"
            ? "Acrésc.:"
            : "Dsct.:";
        if (tipo === "percentual" || tipoCaixa === "percentual") {
            const convertido = base * (valor / 100);
            const convertidoCaixa = baseCaixa * (valorCaixa / 100);
            $label.text(`${prefixo} R$ ${formatBR(convertido)}`);
            $labelCaixa.text(`${prefixo} R$ ${formatBR(convertidoCaixa)}`);
        }
        else if (tipo === "valor" || tipoCaixa === "valor") {
            const convertido = base ? (valor / base) * 100 : 0;
            const convertidoCaixa = baseCaixa ? (valorCaixa / baseCaixa) * 100 : 0;
            $label.text(`${prefixo} ${formatBR(convertido)}%`);
            $labelCaixa.text(`${prefixo} ${formatBR(convertidoCaixa)}%`);
        }
    }
    function calcularTotal() {
        const vl = parseBR($('#id_preco_unitP').val());
        const vlCaixa = parseBR($('#id_preco_unitEd').val());
        const qtd = parseBR($('#id_quantidadeP').val()) || 0;
        const qtdCaixa = parseBR($('#id_quantidadeEd').val()) || 0;
        const at = ($("#id_atribuir").val() || '').trim().toLowerCase();
        const atCaixa = ($("#id_atribuirEd").val() || '').trim().toLowerCase();
        const tipo = ($("#id_tipo_desc_acres").val() || '').trim().toLowerCase();
        const tipoCaixa = ($("#id_tipo_desc_acresEd").val() || '').trim().toLowerCase();
        const valorExtra = parseBR($('#id_desc_acres').val());
        const valorExtraCaixa = parseBR($('#id_desc_acresEd').val());
        let total = vl * qtd;
        let totalCaixa = vlCaixa * qtdCaixa;
        if (at === "desconto" || atCaixa === "desconto" ) {
            if (tipo === "valor" || tipoCaixa === "valor") {
                total -= valorExtra;
                totalCaixa -= valorExtraCaixa;
            } else if (tipo === "percentual" || tipoCaixa === "percentual") {
                total -= total * (valorExtra / 100);
                totalCaixa -= totalCaixa * (valorExtraCaixa / 100);
            }
        }
        else if (at === "acréscimo" || atCaixa === "acréscimo") {
            if (tipo === "valor" || tipoCaixa === "valor") {
                total += valorExtra;
                totalCaixa += valorExtraCaixa;
            } else if (tipo === "percentual" || tipoCaixa === "percentual") {
                total += total * (valorExtra / 100);
                totalCaixa += totalCaixa * (valorExtraCaixa / 100);
            }
        }
        if (total < 0) total = 0;
        if (totalCaixa < 0) totalCaixa = 0;
        $('#id_vl_total_preco').val(formatBR(total));
        $('#id_vl_total_precoEd').val(formatBR(totalCaixa));
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
            $('#id_preco_unitP').val('0,00');
            $('#id_vl_total_preco').val('0,00');
            $('#id_desc_acres').val('0,00');
        }
        controlarPreco();
    });
    $('#edProdModalItem').on('shown.bs.modal', function () {
        atualizarLabel();
        calcularTotal();
    });
    $('#edProdModalP').on('hidden.bs.modal', function () {
        trEditando = null;
        $('#id_cod_produtoP').prop('disabled', false);
    });
    $('#id_quantidadeP, #id_preco_unitP, #id_desc_acres, #id_atribuir, #id_tipo_desc_acres, #id_quantidadeEd, #id_preco_unitEd, #id_desc_acresEd, #id_atribuirEd, #id_tipo_desc_acresEd')
    .on('input change keyup', function () {
        calcularTotal();
        atualizarLabel();
    });
    $("#id_tipo_desc_acres, #id_tipo_desc_acresEd").on('change', function () {
        atualizarLabel();
        calcularTotal();
    });
    $('.addQtdP, .remQtdP').on('click', function () {setTimeout(calcularTotal, 50);});
    $('.addQtdEd, .remQtdEd').on('click', function () {setTimeout(calcularTotal, 50);});
    $('#id_alt_vlP, #id_alt_vlEd').on('change', function () {
        const valor = $(this).val();
        if (valor === "Sim") {
            verificarPermissaoAntesDeExecutar(
                'pedidos.alt_vl_ped',
                function () {
                    // ✅ Permitido
                    $('#id_preco_unitP').prop('disabled', false);
                    $('#id_preco_unitEd').prop('disabled', false);
                },
                function () {
                    // ❌ Negado
                    $('#id_alt_vlP').val('Não'); // volta pro padrão
                    $('#id_alt_vlEd').val('Não');
                    $('#id_preco_unitP').prop('disabled', true);
                    $('#id_preco_unitEd').prop('disabled', true);
                    toast(`Seu usuário não pode alterar valor de produtos no caixa/pedidos!`, "warning");
                }
            );
        } else {
            // Se for "Não", só bloqueia
            $('#id_preco_unitP').prop('disabled', true);
            $('#id_preco_unitEd').prop('disabled', true);
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
                                <td>${produto.id}</td><td>${produto.desc_prod}</td><td>${produto.unidProd}</td><td class="${estoqueClass}">${formatBR(produto.estoque_prod)}</td>
                                <td class="fw-bold">${formatBR(produto.vl_prod)}</td>
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
        $(`.valor-prod[data-porta="${portaAtiva}"]`).val(vl);
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
                                <td>${produto.id}</td><td>${produto.desc_prod}</td><td>${produto.unidProd}</td><td class="${estoqueClass}">${formatBR(produto.estoque_prod)}</td>
                                <td class="fw-bold">${formatBR(produto.vl_prod)}</td>
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
        $(`.valor-prod-adc[data-porta="${portaAdcAtiva}"]`).val(formatBR(vl));
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
        $("#det_cor_porta option").each(function () {
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
        var corPSelecionada = $("#det_cor_porta").val();
        var novaCor = cores[corSelecionada] || "#FFFFFF";
        var novaCorP = cores[corPSelecionada] || "#FFFFFF";
        $("#id_cor").css({"background-color": novaCor, "color": isCorEscura(novaCor) ? "#FFFFFF" : "#000000"});
        $("#det_cor_porta").css({"background-color": novaCorP, "color": isCorEscura(novaCorP) ? "#FFFFFF" : "#000000"});
    }
    $("#id_cor").on("change", atualizarCor);
    $("#det_cor_porta").on("change", atualizarCor);
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
            if (v !== input.val()) {input.val(v);}
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
    $("#id_tel, #id_celular, #id_whatsapp").on("input", function () {maskInput($(this));});
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
        }
        else {$("#fantasia_fantasia").attr("hidden", true).text("");}
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
    $("#django-messages").length && JSON.parse($("#django-messages").attr("data-messages")).forEach(msg => toast(msg.text, msg.tag));
    $(".copiar").on("click", function () {
        let link = $(this).closest(".btn-group").find(".link-rillpay").attr("href");
        if (!link) {
            console.error("Link não encontrado!");
            return; // Se o link não for encontrado, sair da função
        }
        if (navigator.clipboard) {
            navigator.clipboard.writeText(link).then(() => {
                toast(`Link copiado!`, "success");
            }).catch(err => console.error("Erro ao copiar: ", err));
        } else {
            let tempInput = $("<input>");
            $("body").append(tempInput);
            tempInput.val(link).select();
            document.execCommand("copy");
            tempInput.remove();
            toast(`Link copiado!`, "success");
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
        setTimeout(() => {
            limparBackdropsDuplicados();
        }, 450);
    }
    $(document).on('shown.bs.modal', '.modal', function () {
        limparBackdropsDuplicados();
    });
    // Modal de filial
    $(".btn-delete").on("click", function () {
        const orcamentoId = $(this).data("orcamento-id");
        const menuEl = $("#menuModal" + orcamentoId)[0];
        const deleteEl = $("#modal-" + orcamentoId)[0];
        const modalMenu = bootstrap.Modal.getInstance(menuEl);
        const modalDelete = bootstrap.Modal.getOrCreateInstance(deleteEl);
        $(menuEl).one("hidden.bs.modal", function () {
            modalDelete.show();
        });
        modalMenu.hide();
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
        else if (keyCode === 78 || keyCode === 27) {
            closeStaticBackdrop();
            limparBackdropsDuplicados();
        }
    });
    $(document).on('keydown', function (e) {
        if ($(e.target).is('input') || $(e.target).is('textarea') || $(e.target).is('select') || $(e.target).prop('contenteditable')){return;}
        const modalAberto = $('.modal.show');
        if (!modalAberto.length) return;
        const key = e.which || e.keyCode;
        if (key === 83) {modalAberto.find('.btn-confirmar').trigger('click');}
        else if (key === 78 || key === 27) {
            closeStaticBackdrop();
            limparBackdropsDuplicados();
            modalAberto.find('[data-bs-dismiss="modal"]').trigger('click');
        }
    });
    // Função de Desconto - Orçamentos
    function extrairNumero(str) {return parseBR(str) || 0;}
    // Função de cálculo do desconto e atualização do auxiliar
    function calcularDescontoAtualizarAuxiliar() {
        let tipo_desconto = $('#tipo_desconto').val();
        let $campo = $('#campo_desconto');
        let campoDigitado = $campo.val();
        // Ctrl + A + Delete → força 0.00 no input
        if (campoDigitado === '') {
            $campo.val('0,00');
            campoDigitado = '0';
        }
        campoDigitado = campoDigitado;
        let campo_desconto = parseBR(campoDigitado);
        if (isNaN(campo_desconto)) {
            campo_desconto = 0;
            $campo.val('0,00');
        }
        let subtotal_orcamento = extrairNumero($('#subtotal_txt').text());
        let labelNomeCampo = $("label[for='campo_desconto']");
        let labelNomeCampoAuxiliar = $("label[for='auxiliar_desconto']");
        let simboloInputCampo = $("#simbolo");
        let simboloInputCampoAuxiliar = $("#simboloAuxiliar");
        if (subtotal_orcamento === 0) {
            $('#auxiliar_desconto').val('0,00');
            return 0;
        }
        if (tipo_desconto === "valor") {
            labelNomeCampo.text("Valor:");
            simboloInputCampo.text("R$");
            labelNomeCampoAuxiliar.text("Percentual:");
            simboloInputCampoAuxiliar.text("%");
            let percentual = (campo_desconto / subtotal_orcamento) * 100;
            $('#auxiliar_desconto').val(isNaN(percentual) ? '0,00' : formatBR(percentual));
            return campo_desconto;
        } else {
            labelNomeCampo.text("Percentual:");
            simboloInputCampo.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliar.text("R$");
            let valorCalculado = (subtotal_orcamento * campo_desconto) / 100;
            $('#auxiliar_desconto').val(isNaN(valorCalculado) ? '0,00' : formatBR(valorCalculado));
            return valorCalculado;
        }
    }
    $("#campo_desconto, #tipo_desconto").on("input keyup change", function () {calcularDescontoAtualizarAuxiliar();});
    // Evento ao abrir o modal
    $('#modalDesconto').on('shown.bs.modal', function () {$('#tipo_desconto').focus();});
    // Evento botão confirmar
    $('#confirmarDesconto').on('click', function () {
        let desconto = calcularDescontoAtualizarAuxiliar();
        desconto = parseBR(desconto) || 0;
        $('#id_desconto').val(formatBR(desconto));
        $('#desconto_txt').text('R$ ' + formatBR(desconto));
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
            $campo.val('0,00');
            campoDigitado = '0';
        }
        campoDigitado = campoDigitado;
        let campo_acrescimo = parseBR(campoDigitado);
        if (isNaN(campo_acrescimo)) {
            campo_acrescimo = 0;
            $campo.val('0,00');
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
            $('#auxiliar_acrescimo').val(isNaN(percentual) ? '0,00' : parseBR(percentual));
            return campo_acrescimo;
        } else {
            labelNomeCampo.text("Percentual:");
            simboloInputCampoAc.text("%");
            labelNomeCampoAuxiliar.text("Valor:");
            simboloInputCampoAuxiliarAc.text("R$");
            let valorCalculado = ((subtotal_orcamento * campo_acrescimo) / 100);
            $('#auxiliar_acrescimo').val(isNaN(valorCalculado) ? '0,00' : parseBR(valorCalculado));
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
        $('#id_acrescimo').val(parseBR(acrescimo));
        $('#acrescimo_txt').text('R$ ' + formatBR(acrescimo));
        $('#modalAcrescimo').modal('hide');
        atualizarSubtotal();
    });
    $('#exampleModal').on('shown.bs.modal', function () {$('#cid_emp').focus();});
    $('#confirmBtn, #confirmBtn1').click(function () {
        $('#staticBackdrop2').modal('hide');
        $('#gerarVisitasModal').modal('hide');
    });
    $('#tabelas-lista').addClass('table-hover');
    $('.form-control').addClass('form-control-sm');
    $('.form-select').addClass('form-select-sm');
    $("#data-btn").addClass('btn-sm');
    function verificarEstadoUsarData() {
        const usarDataAtivo = $('#usar-data').val() === 'Sim';
        $('#data, #data_inicio, #data_fim, #data_inicio1, #data_inicio2, #data_fim2, #data_fim1').prop('disabled', !usarDataAtivo);
    }
    function verificarBtnPintura() {
        const ativarPintura  = $('#id_pintura').val() === 'Sim';
        const ativarPinturaP = $('#det_pintura_porta').val() === 'Sim';

        $('#id_cor').prop('disabled', !ativarPintura);
        $('#det_cor_porta').prop('disabled', !ativarPinturaP);

        // Só limpa se desativou — não limpa se já tem valor selecionado
        if (!ativarPintura)  $('#id_cor').val("");
        if (!ativarPinturaP) $('#det_cor_porta').val("");

        atualizarCor();
    }

    // Chama nos eventos de mudança também
    $('#id_pintura').on('change', verificarBtnPintura);
    $('#det_pintura_porta').on('change', verificarBtnPintura);

    verificarBtnPintura();
    verificarEstadoUsarData();
    verificarEstadoSwitch('#switchData', '#dtVisita, #pxVisita');
    verificarEstadoSwitch('#switchIdSis', '#prin');
    verificarEstadoSwitch('#switchIdSis1', '#prin1');
    $('#usar-data').change(verificarEstadoUsarData);
    $('#id_pintura, #det_pintura_porta').change(verificarBtnPintura);
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
        }, 50);
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
            if (data.phones && data.phones.length > 0) {$('#id_tel, #id_celular, #id_whatsapp, #id_contato_administrador').val(mascaraFone(data.phones[0].area + " " + data.phones[0].number || ""));}
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
                }).catch(error => {
                    console.error('Erro na verificação de localização:', error);
                    setTimeout(() => fecharLoading(), 500);
                });
                $('#id_endereco').val((data.logradouro || "").toUpperCase());
                $('#id_numero').val((data.numero || "").toUpperCase());
                $('#id_complem').val((data.complemento ? removeAccents(data.complemento) : "").toUpperCase());
                $('#id_bairro_emp').val(bairro);
                $('#id_cidade_emp').val(cidade);
                $('#id_uf_emp').val(estado);
            }).catch(error => {
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
    $('.tab-container').each(function () {
        const container = $(this);
        function abrirSecao(secao, botao) {
            container.find('.form-section').hide();
            container.find('#' + secao).show();
            container.find('.menu-btn').removeClass('btn-ativo').addClass('btn-inativo');
            $(botao).removeClass('btn-inativo').addClass('btn-ativo');
        }
        container.find('.menu-btn').on('click', function () {abrirSecao($(this).data('section'), this);});
        const inicial = container.find('.form-section.active-section').first();
        if (inicial.length) {abrirSecao(inicial.attr('id'), container.find('.menu-btn[data-section="' + inicial.attr('id') + '"]'));}
    });
    $('#id_serial, #id_nome_empresa, #id_nome_emp, #id_desc_prod').focus();
    // $('#loadingModal').modal({keyboard: true, backdrop: 'static'});
    // Fornecedores
    $('#fornecedor, #id_forn, #id_fornecedor').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/fornecedores/lista_ajax/')}).on('select2:open', focSel2);
    // Vendedores
    $('#dadosVendedor, #vendedor, #vendedor_r_ped, #id_vend, #id_vendedor').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/vendedores/lista_ajax/')}).on('select2:open', focSel2);
    // Clientes
    $('#dadosCliente, #cliente, #id_cli, #id_cliente').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/clientes/lista_ajax/')}).on('select2:open', focSel2);
    // Cidades
    $('#id_cidade_fil, #id_cidade').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/cidades/lista_ajax/')}).on('select2:open', focSel2);
    // Estados
    $('#id_uf').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/estados/lista_ajax/')}).on('select2:open', focSel2);
    // Estoques
    $('#id_estoque_padrao').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/estoques/lista_ajax/')}).on('select2:open', focSel2);
    // Informações
    $('#id_observacao_nfe').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/informacoes/lista_ajax/')}).on('select2:open', focSel2);
    // Produtos
    $('#id_produto').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/produtos/lista_ajax1/')}).on('select2:open', focSel2);
    // Técnicos
    $('#id_solicitante, #tecnico, #id_tec').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/tecnicos/lista_ajax/')}).on('select2:open', focSel2);
    // Filiais
    $('#filial, #id_filial, #vinc_emp, #id_vinc_emp, [id^=filial_cr], [id^=filial_cp], #id_filial_user, #id_vinc_fil').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/filiais/lista_ajax/')}).on('select2:open', focSel2);
    // Usuários
    $('#usuario').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/usuarios/lista_ajax/')}).on('select2:open', focSel2);
    // Empresas
    $('#emp, #id_empresa').select2({
        placeholder:opSel, allowClear:true, minimumInputLength:1, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/empresas/lista_ajax/')}).on('select2:open', focSel2);
    // PDVs
    $('#id_terminal').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/pdvs/lista_ajax/')}).on('select2:open', focSel2);
    // Grupos de Regras
    $('#id_grupo_regra').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/grupo_regras/lista_ajax/')}).on('select2:open', focSel2);
    // Regras de Produto
    $('#id_regra').select2({
        placeholder: opSel, allowClear: true, templateResult: renderRegra, templateSelection: d => d.text, language: lingSel, ajax: ajaxRegras('/regras_produto/lista_ajax/')}).on('select2:open', focSel2);~
    // Tabelas de Preço
    $('#dadosTabelaPrecos, #tb-prec, #id_tabela_preco, #id_tb_preco, #id_tabela').select2({
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
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/bancos/lista_ajax/')}).on('select2:open', focSel2);
    // Formas de Pagamento
    $('#forma_saida, #forma_entrada, .forma-pgto, #id_formas_pgto, #id_form_pgto, [id^="formas_pgto_cr"], [id^="formaPgtoSelect-"]').each(function () {
        const $sel = $(this);
        const $modalPai = $sel.closest('.modal');
        $sel.select2({placeholder: opSel, allowClear: true, templateResult: rendOpt, templateSelection: d => d.text, language: lingSel,
            ajax: ajSel2('/formas_pgto/lista_ajax/'), dropdownParent: $modalPai.length ? $modalPai : $(document.body) // 🔥 AQUI
        }).on('select2:open', focSel2);
    });
    // Tipos de Cobrança
    $('#selTpCob, #id_tp_conta, #id_tp_cobranca').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/tp_cobrancas/lista_ajax/')}).on('select2:open', focSel2);
    // Grupos
    $('#grupo, #grupo1, #campo-grupo-produto').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/grupos/lista_ajax/')}).on('select2:open', focSel2);
    // Marcas
    $('#marca, #marca1, #campo-marca-produto').select2({
        placeholder:opSel, allowClear:true, templateResult:rendOpt, templateSelection:d=>d.text, language:lingSel, ajax:ajSel2('/marcas/lista_ajax/')}).on('select2:open', focSel2);
    // Bairros
    $.fn.addNovoInline = function(opts) {
        return this.each(function() {
            var $wrap    = $(this);
            var $selArea = $wrap.find('[id$="-select-area"]');
            var $inpArea = $wrap.find('[id$="-input-area"]');
            var $input   = $inpArea.find('input[type=text]');
            var $btnNovo = $wrap.find('[id^="btn-novo-"]');
            var $btnOk   = $wrap.find('[id^="btn-confirmar-"]');
            var $btnCan  = $wrap.find('[id^="btn-cancelar-"]');
            var $select  = $selArea.find('select');

            // ── Select2 ──────────────────────────────────
            if (opts.select2) {
                $select.select2(opts.select2).on('select2:open', focSel2);
            }

            function abrir() {
                $select.select2('close');
                $selArea.hide(); $inpArea.show();
                $btnNovo.hide(); $btnOk.show(); $btnCan.show();
                $input.val('').focus();
            }
            function fechar() {
                $selArea.show(); $inpArea.hide();
                $btnNovo.show(); $btnOk.hide(); $btnCan.hide();
            }
            function salvar() {
                var nome = $.trim($input.val());
                if (!nome) { $input.focus(); return; }
                $btnOk.prop('disabled', true);
                $.post(opts.url, { nome: nome, csrfmiddlewaretoken: CSRF_TOKEN })
                    .done(function(res) {
                        if (res.erro) { alert(res.erro); return; }
                        var $opt = $select.find('option[value="' + res.id + '"]');
                        if ($opt.length) {
                            $select.val(res.id);
                        } else {
                            $select.append(new Option(res.nome, res.id, true, true));
                        }
                        // Notifica o Select2 da mudança
                        $select.trigger('change');
                        toast('Registro criado com sucesso!', 'success');
                        if (!res.criado) {
                            alert('"' + res.nome + '" já existe e foi selecionado.');
                        }
                        fechar();
                    })
                    .fail(function(xhr) {
                        var msg = xhr.responseJSON?.erro || 'Erro na requisição.';
                        alert(msg);
                    })
                    .always(function() { $btnOk.prop('disabled', false); });
            }

            $btnNovo.on('click', abrir);
            $btnCan.on('click', fechar);
            $btnOk.on('click', salvar);
            $input.on('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); salvar(); }
                if (e.key === 'Escape') fechar();
            });
        });
    };

    // ─── Init ────────────────────────────────────────
    var CSRF_TOKEN = $('[name=csrfmiddlewaretoken]').val();

    $('#bairro-wrapper').addNovoInline({
        url: '/bairros/add-ajax/',
        select2: {
            placeholder: opSel,
            allowClear: true,
            templateResult: rendOpt,
            templateSelection: d => d.text,
            language: lingSel,
            ajax: ajSel2('/bairros/lista_ajax/')
        }
    });
    $('#marca-wrapper').addNovoInline({
        url: '/marcas/add-ajax/',
        select2: {
            placeholder: opSel,
            allowClear: true,
            templateResult: rendOpt,
            templateSelection: d => d.text,
            language: lingSel,
            ajax: ajSel2('/marcas/lista_ajax/')
        }
    });
    $('#grupo-wrapper').addNovoInline({
        url: '/grupos/add-ajax/',
        select2: {
            placeholder: opSel,
            allowClear: true,
            templateResult: rendOpt,
            templateSelection: d => d.text,
            language: lingSel,
            ajax: ajSel2('/grupos/lista_ajax/')
        }
    });
    $('#unidade-wrapper').addNovoInline({
        url: '/unidades/add-ajax/',
        select2: {
            placeholder: opSel,
            allowClear: true,
            templateResult: rendOpt,
            templateSelection: d => d.text,
            language: lingSel,
            ajax: ajSel2('/unidades/lista_ajax/')
        }
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
    const seletorAutoData = '[id^="dt_pag_cr-"], [id^="cel-dt-"], [id^="dt_pag_cp-"], #id_data_vencimento, .dt-fat-orcamento, .dt-fat-pedido, #id_dt_inicio, #id_dt_venc, #data, #id_dt_emi, #dt_efet_ent, #inpDtPriParc, #id_dt_prev_instalacao, #id_dt_ent, #id_data_aniversario, #id_data_emissao, #data_inicio1, #data_emi_ini1, #data_emi_fim1, #data_ent_ini1, #data_ent_fim1, #data_inst_ini1, #data_inst_fim1, #data_fim1, #data_inicio2, #data_fim2, #id_data_doc, #id_data_prop, #id_dt_visita, #dtVisita, #id_dt_criacao';
    $(seletorAutoData).each(function () {if (!$(this).val()) {$(this).val(obterDataAtual2());}});
    if ($('#id_qtd, #id_quantidade').val() === '') {$('#id_qtd, #id_quantidade').val('1.00');}
    if ($('#id_rolo').val() === '') {$('#id_rolo').val('0.60');}
    if ($('#id_qtd_mens, #id_qtd_parcelas').val() === '') {$('#id_qtd_mens, #id_qtd_parcelas').val('1');}
    if ($('#id_valor, #id_juros, #id_multa, #id_vl_mens, #id_valor_mensalidade, #id_preco_unit, #id_vl_prod').val() === '') {$('#id_valor, #id_juros, #id_multa, #id_vl_mens, #id_valor_mensalidade, #id_preco_unit, #id_vl_prod').val('0,00');}
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
    const seletorMascaraData = '[id^="dt_pag_cr-"], [id^="cel-dt-"], [id^="dt_pag_cp-"], #id_data_vencimento, #id_dt_inicio, #data, .dt-fat-orcamento, .dt-fat-pedido, #id_dt_emi, #dt_efet_ent, #inpDtPriParc, #id_dt_prev_instalacao, #id_dt_ent, #id_dt_venc, #id_data_aniversario, #id_data_prop, #id_data_certificado, #id_data_nascimento, #id_data_nascimento_administrador, #data_inicio1, #data_emi_ini1, #data_emi_fim1, #data_ent_ini1, #data_ent_fim1, #data_inst_ini1, #data_inst_fim1, #data_fim1, #data_inicio2, #data_fim2, #id_data_emissao, #id_data_entrega, #id_dt_criacao';
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
        if (valor === '' || valor === null || valor === undefined) {return '0,00';}
        let num = parseBR(valor);
        if (isNaN(num)) {num = 0;}
        return formatInputBR(num);
    }
    if ($("#id_qtd_usu, #id_qtd_ass").val() === '') {$("#id_qtd_usu, #id_qtd_ass").val('1');}
    if ($("#id_desc_imp").val() === '') {$("#id_desc_imp").val('IMPLANTAÇÃO/TREINAMENTO');}
    if ($("#id_desc_ass").val() === '') {$("#id_desc_ass").val('ASSESSORIA MENSAL');}
    let selectors = '#id_peso_m2, #id_espessura_lam, #det_largura_passagem, #det_altura_passagem, #id_diametro_eixo, #id_limite_credito, #id_desconto_maximo, #id_acrescimo_maximo, #id_limite_credito_padrao, #id_estoque_minimo, #id_estoque_maximo, #id_desc_acresEd, #id_preco_unitEd, #id_lg_ps, #id_at_ps, #vl_saida, #vl_entrada, #id_vl_imp, #id_dsct_imp, #id_vl_fin_imp, #id_vl_ass, #id_dsct_ass, #id_vl_fin_ass, #id_vl_p_s, #editValorItemInput, #editValorItemAdcInput, #valorPgto, .money, #id_quantidadeP, #id_quantidadeEd, #id_vl_form_pgto, #id_multi_m2, #id_multi_lg_corte1, #id_multi_lg_corte2, #id_multi_lg_corte3, .inp-valor-pgto, #id_desc_acres, #id_preco_unitP, [id^=desc_m_cr], [id^=desc_j_cr], [id^="cel-parcela-"], [id^=desc_m_cp], [id^=desc_j_cp], [id^=juros_cr], [id^=juros_cp], [id^=multa_cr], [id^=multa_cp], [id^=vl_pg_cr], [id^=vl_pg_cp], .inp-valor, #id_valor, #id_juros, #id_multa, #id_vl_juros, #id_vl_multa, #id_ft_juros, #id_ft_multa, .valor-prod, .valor-prod-adc, .qtd-prod-adc, .qtd-prod, #campo_1, #campo_2, #id_margem, #id_vl_prod, #id_vl_tab, #id_vl_tabEnt, .inpFrete, #id_quantidade, #total-frete, .editable, #id_preco_unit, #id_valor_mensalidade, #id_vl_mens, #id_qtd, #id_m2, #id_acrescimo, #id_desconto, #id_vl_compra, #id_vl_compra_adc, #id_estoque_prod, #campo_desconto, #campo_acrescimo';
    function calcDscoImp() {
        const imp = parseBR($("#id_vl_imp").val());
        const dsct = parseBR($("#id_dsct_imp").val());
        const calc = imp - dsct;
        $("#id_vl_fin_imp").val(formatBR(calc));
    }
    calcDscoImp();
    $('#id_vl_imp, #id_dsct_imp').on('input keyup change', function () {calcDscoImp();});
    function calcDscoAss() {
        const ass = parseBR($("#id_vl_ass").val());
        const dsct = parseBR($("#id_dsct_ass").val());
        const calc = ass - dsct;
        $("#id_vl_fin_ass").val(formatBR(calc));
    }
    calcDscoAss();
    $('#id_vl_ass, #id_dsct_ass').on('input keyup change', function () {calcDscoAss();});
    $(document).on('input', selectors, function() {aplicarMascaraMoney(this);});
    $(document).on('blur', selectors, function() {
        const valor = parseBR($(this).val()) || 0;
        $(this).val(formatBR(valor));
    });
    // Inicializa valores existentes
    $(selectors).each(function() {
        if ($(this).val()) {$(this).val(formatBR(parseBR($(this).val())));}
    });
    $(selectors).each(function () {$(this).val(normalizarNumero($(this).val()));});
    $(document).on('input', selectors, function () {
        let valor = $(this).val();
        if (valor === '') {
            $(this).val('0,00');
            return;
        }
        let num = parseBR(valor);
        if (isNaN(num)) {$(this).val('0,00');}
    });
    function aplicarFormatoInicialBR(contexto = document) {
        $(contexto).find(selectors).each(function () {
            const valor = $(this).val();
            if (valor !== '' && valor !== null && valor !== undefined) {$(this).val(formatBR(valor));}
        });
    }
    aplicarFormatoInicialBR();
    const campoData = $('#id_data_aniversario');
    const campoDataAniversario = $('#id_id_data_aniversario');
    campoData.on('input', function () {campoDataAniversario.val(campoData.val());});
    const dataPesquisaInput = $("#data_pesquisa");
    const today = new Date().toISOString().slice(0, 10);
    dataPesquisaInput.val(today);
    // Listagem de Orçamentos no modal
    function montarTabelaItens(itens) {
        if (!itens || !itens.length) {return `<div class="text-center text-muted py-3">Nenhum item encontrado.</div>`;}
        let linhas = "";
        itens.forEach(function(item) {
            linhas += `
                <div class="list-group-item py-1 item-lista">
                    <div class="row align-items-center linha-lista">
                        <!-- Itens -->
                        <div class="col-md-1 fw-bold codigo-col" data-label="Item:"><small>${item.item}</small></div>
                        <!-- Código -->
                        <div class="col-md-1 text-center fw-bold text-secondary codigo-col" data-label="Código:"><small>#${item.codigo}</small></div>
                        <!-- Descrição -->
                        <div class="col-md-3 fw-semibold descricao-col" data-label="Descrição:"><small>${item.produto}</small></div>
                        <!-- Unidade -->
                        <div class="col-md-1 fw-bold codigo-col" data-label="Unidade:"><small>${item.unidade || ''}</small></div>
                        <!-- Valor Unitário -->
                        <div class="col-md-2 fw-bold text-success codigo-col" data-label="Vl. Unit.:"><small>R$ ${formatBR(item.valor_unit)}</small></div>
                        <!-- Quantidade -->
                        <div class="col-md-2 fw-bold codigo-col" data-label="Qtde.:"><small>${formatBR(item.qtd)}</small></div>
                        <!-- Valor Total -->
                        <div class="col-md-2 fw-bold text-success codigo-col" data-label="Vl. Total:"><small>R$ ${formatBR(item.valor_total)}</small></div>
                    </div>
                </div>
            `;
        });
        return `
            <div class="card border-0 shadow-sm rounded-3 overflow-hidden mb-4">
                <div class="list-group" style="max-height: 150px; overflow-y: auto;">
                    <!-- Cabeçalho -->
                    <div class="list-group-item bg-light fw-bold cabecalho-lista">
                        <div class="row align-items-center">
                            <div class="col-md-1 text-center border-end"><small>Itens</small></div>
                            <div class="col-md-1 text-center border-end"><small>Cód.</small></div>
                            <div class="col-md-3 border-end"><small>Descrição</small></div>
                            <div class="col-md-1 border-end"><small>UN</small></div>
                            <div class="col-md-2 border-end"><small>Vl. Unit.</small></div>
                            <div class="col-md-2 border-end"><small>Qtde.</small></div>
                            <div class="col-md-2"><small>Vl. Total</small></div>
                        </div>
                    </div>
                    ${linhas}
                </div>
            </div>
        `;
    }
    $(document).on("click",".foto-item img",function(e){
        e.stopPropagation();
        $("#viewerImagem").attr("src",$(this).attr("src"));
        $("#fotoViewer").fadeIn(150).css("display","flex");
    });
    // fechar no X
    $(document).on("click",".fechar-viewer",function(){
        $("#fotoViewer").fadeOut(150);
    });
    // fechar clicando fora
    $(document).on("click","#fotoViewer",function(e){
        if(e.target===this)
            $(this).fadeOut(150);
    });
    // ESC
    $(document).on("keydown",function(e){
        if(e.key==="Escape")
            $("#fotoViewer").fadeOut(150);
    });
    $(document).on("click",".foto-preview",function(){
        $("#viewerImagem").attr("src",$(this).data("url"));
        $("#fotoViewer").css("display","flex").hide().fadeIn(180);
    });
    function montarFotosPorta(fotos){
        if(!fotos || !fotos.length)
            return '<div class="text-center text-muted py-2">Nenhuma foto.</div>';
        let html='<div class="d-flex flex-wrap gap-2">';
        fotos.forEach(function(f){
            html+=`
                <img src="${f.url}" data-url="${f.url}" class="foto-preview img-thumbnail" style="width:90px;height:90px;object-fit:cover;border-radius:8px;cursor:pointer;transition:.2s">
            `;
        });
        html+='</div>';
        return html;
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
            const fotos = montarFotosPorta(porta.fotos);
            html += `
                <div class="accordion-item mb-2">
                    <h2 class="accordion-header" id="${headingId}">
                        <button class="accordion-button ${collapsed} bg-body-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#${collapseId}" aria-expanded="${ariaExpanded}" aria-controls="${collapseId}" style="max-height: 30px;">
                            <strong>${titulo}</strong>
                        </button>
                    </h2>
                    <div id="${collapseId}" class="accordion-collapse collapse ${aberto}" aria-labelledby="${headingId}" data-bs-parent="#accordion_${tipo}_${responseId}">
                        <div class="accordion-body">
                            ${montarTabelaItens(itens)}
                            <hr>
                            <label class="fw-bold mb-2">Fotos da Porta</label>
                            ${fotos}
                        </div>
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
                portaDetalhes = {};
                portaFotos = {};
                response.portas.forEach(function(porta){
                    portaDetalhes[porta.numero] = porta.detalhes || {};
                    portaFotos[porta.numero] = (porta.fotos || []).map(function(f){
                        return{id: f.id, url: f.url, principal: f.principal, ordem: f.ordem, criado_em: f.criado_em, novo:false};
                    });
                });
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
                    situacaoTexto = response.situacao;
                }
                else {situacaoColor = "#B22222";}
                const produtosAccordion = montarAccordionPortas(response.portas, 'produtos', response.id);
                const adicionaisAccordion = montarAccordionPortas(response.portas, 'adicionais', response.id);
                $(`#infoEntBody`).html(`
                    <div class="row">
                        <div class="col-md-2">
                            <label class="form-label">Nº Orçamento</label>
                            <input class="form-control form-control-sm fw-semibold" value="${response.id}" disabled>
                        </div>
                        <div class="col-md-5">
                            <label class="form-label">Filial</label>
                            <input class="form-control form-control-sm fw-semibold" value="${response.cliente.empresa.nome}" disabled>
                        </div>
                        <div class="col-md-5">
                            <label class="form-label">Cliente</label>
                            <input class="form-control form-control-sm fw-semibold" value="${response.cliente.nome}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Solicitante</label>
                            <input class="form-control form-control-sm fw-semibold" value="${response.colaborador}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label">Data Emissão</label>
                            <input class="form-control form-control-sm fw-semibold" value="${response.data_emissao}" disabled>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Data Entrega</label>
                            <input class="form-control form-control-sm fw-semibold" value="${response.data_entrega}" disabled>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Valor Total</label>
                            <input class="form-control form-control-sm fw-semibold" style="color:#2E8B57" value="R$ ${formatBR(response.vl_tot)}" disabled>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label">Situação</label>
                            <input class="form-control form-control-sm fw-semibold" style="background:${situacaoColor};color:white;text-align:center" value="${situacaoTexto}" disabled>
                        </div>
                    </div>
                    <div class="col-12 mt-2">
                        <div class="card" style="margin: 0;">
                            <div class="card-header bg-secondary-subtle d-flex align-items-center gap-2 flex-wrap">
                                <button type="button" class="btn btn-dark btn-sm" id="medidasBtn${response.id}">Produtos</button>
                                <button type="button" class="btn btn-dark btn-sm" id="clienteBtn${response.id}">Adicionais</button>
                                ${statusHTML}
                            </div>
                            <div class="card-body p-1">
                                <div class="form-section" id="medidas${response.id}">${produtosAccordion}</div>
                                <div class="form-section" id="clientes${response.id}" style="display:none;">${adicionaisAccordion}</div>
                            </div>
                        </div>
                    </div>
                    <div class="row mt-2">
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
        if (!itens || !itens.length) {return `<div class="text-center text-muted py-3">Nenhum item encontrado.</div>`;}
        let linhas = "";
        itens.forEach(function(item) {
            const valor = parseBR(item.desconto_acrescimo || 0);
            let sinal = '';
            if (valor !== 0) {sinal = item.tp_desc_acres === 'Desconto' ? '-' : '+';}
            linhas += `
                <tr>
                    <td>${item.item}</td><td>${item.codigo}</td><td>${item.produto}</td> <td>${item.unidade || ''}</td>
                    <td style="font-weight:bold;color:#2E8B57;">R$ ${formatBR(item.valor_unit)}</td>
                    <td>${formatBR(item.qtd)}</td><td>${valor !== 0 ? `${sinal} R$ ${formatBR(valor)}` : ''}</td>
                    <td style="font-weight:bold;color:#2E8B57;">R$ ${formatBR(item.subtotal)}</td>
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
    $(document).on('click', '#icone-pedido, .op-detalhe-pedido', function() {
        iniciarLoading();
        const id = $(this).data('id');
        listarPedido(id);
    });
    function listarPedido(id) {
        $.ajax({
            url: '/pedidos/detalhes_ajax/' + id + '/', type: 'GET', success: function(response) {
                $('#infoEntModalLabel').html(`<strong><i class="fa-solid fa-circle-info text-white"></i> Detalhes - Pedido Nº ${response.id}</strong>`);
                let situacaoColor = "#005eff";
                if (response.situacao === "Faturado") {situacaoColor = "#3CB371";}
                else if (response.situacao === "Cancelado") {situacaoColor = "#B22222";}
                const tabelaItens = montarTabelaItensPedido(response.itens);
                let motivoCancelamento = '';
                if (response.situacao === "Cancelado") {
                    motivoCancelamento = `
                        <div class="row mt-3">
                            <div class="col-md-12">
                                <label class="form-label">Motivo do Cancelamento</label>
                                <textarea class="form-control" disabled>${response.motivo || ''}</textarea>
                            </div>
                        </div>
                    `;
                }
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
                            <input class="form-control form-control-sm fw-bold" style="color:#2E8B57" value="R$ ${formatBR(response.total)}" disabled>
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
                            <div class="card-body">${tabelaItens}</div>
                        </div>
                    </div>
                    <div class="row mt-3">
                        <div class="col-md-12">
                            <label class="form-label">Observações</label>
                            <textarea class="form-control" disabled>${response.obs || ''}</textarea>
                        </div>
                    </div>
                    ${motivoCancelamento}
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
                <div class="col-md-1 border-end text-secondary border-bottom fw-bold descricao-col" data-label="#:">${f.item}</div>
                <div class="col-md-5 border-end border-bottom fw-bold descricao-col" data-label="Forma de Pagamento:">${f.forma}</div>
                <div class="col-md-6 border-bottom fw-bold descricao-col" data-label="Valor:">R$ ${formatBR(f.valor)}</div>
            `;
        });
        return `
            <div class="card border-0 shadow-sm rounded-3 overflow-hidden mb-4">
                <div class="list-group">
                    <!-- Cabeçalho -->
                    <div class="list-group-item bg-light fw-bold cabecalho-lista">
                        <div class="row align-items-center">
                            <div class="col-md-1 border-end">#</div>
                            <div class="col-md-5 border-end">Forma</div>
                            <div class="col-md-6">Valor</div>
                        </div>
                    </div>
                    <div class="list-group-item py-1 item-lista">
                        <div class="row align-items-center linha-lista">
                            ${linhas}
                        </div>
                    </div>
                </div>
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
            url: '/contas_receber/detalhes_ajax/' + id + '/', type: 'GET',
            success: function(response) {
                let cor = "#005eff";
                if (response.situacao === "Aberta") {cor = "#005eff";}
                else if (response.situacao === "Paga") {cor = "#3CB371";}
                else if (response.vencido) { cor = "#B22222";}
                const tabelaFormas = montarTabelaFormasCR(response.formas);
                $('#infoEntModalLabel').html(`<strong><i class="fa-solid fa-file-invoice-dollar text-white"></i> Conta à Receber - Nº ${response.num_conta}</strong>`);
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
                            <input class="form-control form-control-sm fw-bold text-center" style="background:${cor};color:white" value="${response.situacao}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label>Valor</label>
                            <input class="form-control form-control-sm fw-bold text-success" value="R$ ${formatBR(response.valor)}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label>Juros</label>
                            <input class="form-control form-control-sm" value="R$ ${formatBR(response.juros)}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label>Multa</label>
                            <input class="form-control form-control-sm" value="R$ ${formatBR(response.multa)}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label>Desconto</label>
                            <input class="form-control form-control-sm text-danger" value="R$ ${formatBR(response.desconto)}" disabled>
                        </div>
                    </div>
                    <div class="col-12 mt-3">
                        <div class="card">
                            <div class="card-header bg-secondary-subtle text-dark">
                                <strong>Formas de Pagamento</strong>
                            </div>
                            <div class="card-body">${tabelaFormas}</div>
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
    // Lista para Contas A Pagar
    $(document).on('click', '.op-detalhe-cp', function() {
        iniciarLoading();
        const id = $(this).data('id');
        listarContaPagar(id);
    });
    function listarContaPagar(id) {
        $.ajax({
            url: '/contas_pagar/detalhes_ajax/' + id + '/', type: 'GET',
            success: function(response) {
                let cor = "#005eff";
                if (response.situacao === "Aberta") {cor = "#005eff";}
                else if (response.situacao === "Paga") {cor = "#3CB371";}
                else if (response.vencido) { cor = "#B22222";}
                $('#infoEntModalLabel').html(`<strong><i class="fa-solid fa-file-invoice-dollar text-white"></i> Conta à Pagar - Nº ${response.num_conta}</strong>`);
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
                            <label>Fornecedor</label>
                            <input class="form-control form-control-sm fw-bold" value="${response.fornecedor}" disabled>
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
                            <input class="form-control form-control-sm fw-bold text-center" style="background:${cor};color:white" value="${response.situacao}" disabled>
                        </div>
                        <div class="col-md-3">
                            <label>Valor</label>
                            <input class="form-control form-control-sm fw-bold text-success" value="R$ ${formatBR(response.valor)}" disabled>
                        </div>
                        <div class="col-md-4">
                            <label>Juros</label>
                            <input class="form-control form-control-sm" value="R$ ${formatBR(response.juros)}" disabled>
                        </div>
                        <div class="col-md-5">
                            <label>Multa</label>
                            <input class="form-control form-control-sm" value="R$ ${formatBR(response.multa)}" disabled>
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