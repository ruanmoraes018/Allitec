/*global gettext, interpolate, ngettext, Actions*/
'use strict';

{
    function removeAccents(str) {
        return str.normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    }

    function abreviarEndereco(endereco) {
        const abreviacoes = {
            "RUA": "R.",
            "AVENIDA": "AV.",
            "TRAVESSA": "TV.",
            "RODOVIA": "ROD.",
            "ESTRADA": "ESTR.",
            "ALAMEDA": "AL."
        };
        let partes = endereco.split(" ");
        if (abreviacoes[partes[0]]) {
            partes[0] = abreviacoes[partes[0]];
        }
        return partes.join(" ");
    }

    function mascaraFone(fone) {
        fone = fone.replace(/\D/g, "");
        if (fone.length === 10) {
            return fone.replace(/(\d{2})(\d{4})(\d{4})/, "($1) $2-$3");
        } else if (fone.length === 11) {
            return fone.replace(/(\d{2})(\d{5})(\d{4})/, "($1) $2-$3");
        }
        return fone;
    }

    function buscarDadosCNPJ(cnpj) {
        cnpj = cnpj.replace(/\D/g, '');
        const loadingModal = document.getElementById('loadingModal');
        if (loadingModal) loadingModal.classList.add('show');

        fetch(`https://open.cnpja.com/office/${cnpj}`)
            .then(response => response.json())
            .then(data => {
                if (data.company) {
                    document.getElementById('id_razao_social').value = (data.company.name || "").toUpperCase();
                    document.getElementById('id_fantasia').value = (data.alias || "").toUpperCase();
                }
                if (data.registrations && data.registrations.length > 0) {
                    let ie = data.registrations[0].number || "";
                    if (data.registrations[0].state === "PA") {
                        ie = ie.replace(/^(\d{2})(\d{3})(\d{3})(\d{1})$/, '$1.$2.$3-$4');
                    }
                    document.getElementById('id_ie').value = ie;
                }

                let cep = (data.address.zip || "").replace(/^(\d{5})(\d{3})$/, '$1-$2');
                document.getElementById('id_cep').value = cep;

                let endereco = (data.address.street || "").toUpperCase();
                document.getElementById('id_endereco').value = abreviarEndereco(endereco);

                document.getElementById('id_numero').value = data.address.number || "";
                document.getElementById('id_bairro').value = (data.address.district || "").toUpperCase();
                document.getElementById('id_cidade').value = removeAccents((data.address.city || "")).toUpperCase();
                document.getElementById('id_uf').value = (data.address.state || "").toUpperCase();

                if (data.phones && data.phones.length > 0) {
                    const tel = mascaraFone(data.phones[0].area + data.phones[0].number || "");
                    document.getElementById('id_tel').value = tel;
                    document.getElementById('id_tel_adm').value = tel;
                }

                if (data.emails && data.emails.length > 0) {
                    const email = data.emails[0].address || "";
                    document.getElementById('id_email').value = email;
                    document.getElementById('id_email_adm').value = email;
                }

                if (data.company.members?.length > 0) {
                    document.getElementById('id_nome').value = (data.company.members[0].person.name || "").toUpperCase();
                }
            })
            .catch(error => console.error('Erro ao buscar dados do CNPJ:', error))
            .finally(() => {
                setTimeout(() => {
                    if (loadingModal) loadingModal.classList.remove('show');
                }, 3000);
            });
    }

    ready(function () {
        const actionsEls = document.querySelectorAll('tr input.action-select');
        if (actionsEls.length > 0) {
            Actions(actionsEls);
        }

        // NOVO: busca de CNPJ
        const cnpjInput = document.getElementById('id_cnpj');
        if (cnpjInput) {
            cnpjInput.addEventListener('blur', function () {
                if (this.value) {
                    buscarDadosCNPJ(this.value);
                }
            });
        }
    });


    function show(selector) {
        document.querySelectorAll(selector).forEach(function(el) {
            el.classList.remove('hidden');
        });
    }

    function hide(selector) {
        document.querySelectorAll(selector).forEach(function(el) {
            el.classList.add('hidden');
        });
    }

    function showQuestion(options) {
        hide(options.acrossClears);
        show(options.acrossQuestions);
        hide(options.allContainer);
    }

    function showClear(options) {
        show(options.acrossClears);
        hide(options.acrossQuestions);
        document.querySelector(options.actionContainer).classList.remove(options.selectedClass);
        show(options.allContainer);
        hide(options.counterContainer);
    }

    function reset(options) {
        hide(options.acrossClears);
        hide(options.acrossQuestions);
        hide(options.allContainer);
        show(options.counterContainer);
    }

    function clearAcross(options) {
        reset(options);
        const acrossInputs = document.querySelectorAll(options.acrossInput);
        acrossInputs.forEach(function(acrossInput) {
            acrossInput.value = 0;
        });
        document.querySelector(options.actionContainer).classList.remove(options.selectedClass);
    }

    function checker(actionCheckboxes, options, checked) {
        if (checked) {
            showQuestion(options);
        } else {
            reset(options);
        }
        actionCheckboxes.forEach(function(el) {
            el.checked = checked;
            el.closest('tr').classList.toggle(options.selectedClass, checked);
        });
    }

    function updateCounter(actionCheckboxes, options) {
        const sel = Array.from(actionCheckboxes).filter(function(el) {
            return el.checked;
        }).length;
        const counter = document.querySelector(options.counterContainer);
        // data-actions-icnt is defined in the generated HTML
        // and contains the total amount of objects in the queryset
        const actions_icnt = Number(counter.dataset.actionsIcnt);
        counter.textContent = interpolate(
            ngettext('%(sel)s of %(cnt)s selected', '%(sel)s of %(cnt)s selected', sel), {
                sel: sel,
                cnt: actions_icnt
            }, true);
        const allToggle = document.getElementById(options.allToggleId);
        allToggle.checked = sel === actionCheckboxes.length;
        if (allToggle.checked) {
            showQuestion(options);
        } else {
            clearAcross(options);
        }
    }

    const defaults = {
        actionContainer: "div.actions",
        counterContainer: "span.action-counter",
        allContainer: "div.actions span.all",
        acrossInput: "div.actions input.select-across",
        acrossQuestions: "div.actions span.question",
        acrossClears: "div.actions span.clear",
        allToggleId: "action-toggle",
        selectedClass: "selected"
    };

    window.Actions = function(actionCheckboxes, options) {
        options = Object.assign({}, defaults, options);
        let list_editable_changed = false;
        let lastChecked = null;
        let shiftPressed = false;

        document.addEventListener('keydown', (event) => {
            shiftPressed = event.shiftKey;
        });

        document.addEventListener('keyup', (event) => {
            shiftPressed = event.shiftKey;
        });

        document.getElementById(options.allToggleId).addEventListener('click', function(event) {
            checker(actionCheckboxes, options, this.checked);
            updateCounter(actionCheckboxes, options);
        });

        document.querySelectorAll(options.acrossQuestions + " a").forEach(function(el) {
            el.addEventListener('click', function(event) {
                event.preventDefault();
                const acrossInputs = document.querySelectorAll(options.acrossInput);
                acrossInputs.forEach(function(acrossInput) {
                    acrossInput.value = 1;
                });
                showClear(options);
            });
        });

        document.querySelectorAll(options.acrossClears + " a").forEach(function(el) {
            el.addEventListener('click', function(event) {
                event.preventDefault();
                document.getElementById(options.allToggleId).checked = false;
                clearAcross(options);
                checker(actionCheckboxes, options, false);
                updateCounter(actionCheckboxes, options);
            });
        });

        function affectedCheckboxes(target, withModifier) {
            const multiSelect = (lastChecked && withModifier && lastChecked !== target);
            if (!multiSelect) {
                return [target];
            }
            const checkboxes = Array.from(actionCheckboxes);
            const targetIndex = checkboxes.findIndex(el => el === target);
            const lastCheckedIndex = checkboxes.findIndex(el => el === lastChecked);
            const startIndex = Math.min(targetIndex, lastCheckedIndex);
            const endIndex = Math.max(targetIndex, lastCheckedIndex);
            const filtered = checkboxes.filter((el, index) => (startIndex <= index) && (index <= endIndex));
            return filtered;
        };

        Array.from(document.getElementById('result_list').tBodies).forEach(function(el) {
            el.addEventListener('change', function(event) {
                const target = event.target;
                if (target.classList.contains('action-select')) {
                    const checkboxes = affectedCheckboxes(target, shiftPressed);
                    checker(checkboxes, options, target.checked);
                    updateCounter(actionCheckboxes, options);
                    lastChecked = target;
                } else {
                    list_editable_changed = true;
                }
            });
        });

        document.querySelector('#changelist-form button[name=index]').addEventListener('click', function(event) {
            if (list_editable_changed) {
                const confirmed = confirm(gettext("You have unsaved changes on individual editable fields. If you run an action, your unsaved changes will be lost."));
                if (!confirmed) {
                    event.preventDefault();
                }
            }
        });

        const el = document.querySelector('#changelist-form input[name=_save]');
        // The button does not exist if no fields are editable.
        if (el) {
            el.addEventListener('click', function(event) {
                if (document.querySelector('[name=action]').value) {
                    const text = list_editable_changed
                        ? gettext("You have selected an action, but you haven’t saved your changes to individual fields yet. Please click OK to save. You’ll need to re-run the action.")
                        : gettext("You have selected an action, and you haven’t made any changes on individual fields. You’re probably looking for the Go button rather than the Save button.");
                    if (!confirm(text)) {
                        event.preventDefault();
                    }
                }
            });
        }
        // Sync counter when navigating to the page, such as through the back
        // button.
        window.addEventListener('pageshow', (event) => updateCounter(actionCheckboxes, options));
    };

    // Call function fn when the DOM is loaded and ready. If it is already
    // loaded, call the function now.
    // http://youmightnotneedjquery.com/#ready
    function ready(fn) {
        if (document.readyState !== 'loading') {
            fn();
        } else {
            document.addEventListener('DOMContentLoaded', fn);
        }
    }

    ready(function() {
        const actionsEls = document.querySelectorAll('tr input.action-select');
        if (actionsEls.length > 0) {
            Actions(actionsEls);
        }
    });
}
