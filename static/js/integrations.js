const KubernetesIntegration = {
    delimiters: ['[[', ']]'],
    props: ['instance_name', 'display_name', 'logo_src', 'section_name'],
    emits: ['update'],
    template: `
<div
        :id="modal_id"
        class="modal modal-small fixed-left fade shadow-sm" tabindex="-1" role="dialog"
        @dragover.prevent="modal_style = {'height': '300px', 'border': '2px dashed var(--basic)'}"
        @drop.prevent="modal_style = {'height': '100px', 'border': ''}"
>
    <ModalDialog
            v-model:description="description"
            v-model:is_default="is_default"
            @update="update"
            @create="create"
            :display_name="display_name"
            :id="id"
            :is_fetching="is_fetching"
            :is_default="is_default"
    >
        <template #body>
            <div class="form-group">
                <h9>Hostname</h9>
                <input type="text" 
                       v-model="hostname" 
                       class="form-control form-control-alternative"
                       placeholder="Address of kubernetes cluster"
                       :class="{ 'is-invalid': error.aws_access_key }">
                <div class="invalid-feedback">[[ error.hostname ]]</div>
                <h9>Token</h9>
                 <SecretFieldInput 
                        v-model="k8s_token"
                        placeholder="Security token"
                 />
                <div class="invalid-feedback">[[ error.token ]]</div>
               
            </div>
            <h9>Cluster type</h9>
            <div class="row">
                <div class="col-4 pl-0">
                    <input
                            id="radioBtn1"
                            name="radio-group"
                            class="mx-2 custom-radio"
                            type="radio"
                            value="false"
                            v-model="scaling_cluster"
                            >
                    <label
                            class="mb-0"
                            for="radioBtn1">
                        <h9 class="ml-1">
                        Standard                            
                        <button
                            class="btn pl-1"
                            data-toggle="infotip"
                            data-placement="right"
                            title="Cluster doesn't use auto scaling technology.">
                            <i class="fas fa-gray fa-info-circle"></i>
                        </button>
                        </h9>
                    </label>
                </div>
                <div class="col">
                    <input
                        id="radioBtn2"
                        name="radio-group"
                        checked
                        class="mx-2 custom-radio"
                        type="radio"
                        value="true"
                        v-model="scaling_cluster"
                        >
                    <label
                        class="mb-0"
                        for="radioBtn2">
                        <h9 class="ml-1">
                        Auto-scaling
                        <button
                            class="btn pl-1"
                            data-toggle="infotip"
                            data-placement="right"
                            title="Cluster uses auto scaling technology on cloud level.">
                            <i class="fas fa-gray fa-info-circle"></i>
                        </button>
                        </h9>
                    </label>
                </div>
            </div>
            <div class="form-group w-100-imp">                
            <h9>Namespace</h9>
                <div class="custom-input">
                <select class="selectpicker bootstrap-select__b" 
                    v-model="namespace"
                >
                    <option v-for="item in namespaces">[[ item ]]</option>
                </select>
                </div>
            <button type="button" class="btn btn-secondary btn-sm mr-1 d-inline-block"
                @click="get_namespaces"
            >
            Get namespaces
            </button>
            </div>
            <div class="row">
                <div class="col">
                <label class="custom-checkbox d-flex align-items-center">
                    <input class="mr-1" type="checkbox"
                            v-model="secure_connection"
                           >
                    <h9>
                        Secure connection
                    </h9>
                    <button
                        class="btn"
                        data-toggle="infotip"
                        data-placement="right"
                        title="Option determines if the server's SSL certificate should be verified for security or not.">
                        <i class="fas fa-gray fa-info-circle"></i>
                    </button>
                </label>
                </div>
            </div>
        </template>
        <template #footer>
            <test-connection-button
                    :apiPath="api_base + 'check_settings/' + pluginName"
                    :error="error.check_connection"
                    :body_data="body_data"
                    v-model:is_fetching="is_fetching"
                    @handleError="handleError"
            >
            </test-connection-button>
        </template>

    </ModalDialog>
</div>
    `,
    data() {
        return this.initialState()
    },
    mounted() {
        this.modal.on('hidden.bs.modal', e => {
            this.clear()
        })
    },
    computed: {
        apiPath() {
            return this.api_base + 'integration/'
        },
        project_id() {
            return getSelectedProjectId()
        },
        body_data() {
            const {
                k8s_token,
                hostname,
                secure_connection,
                scaling_cluster,
                project_id,
                namespace,
                description,
                is_default,
                status
            } = this
            return {
                k8s_token,
                hostname,
                secure_connection,
                scaling_cluster,
                namespace,
                project_id,
                description,
                is_default,
                status
            }
        },
        modal() {
            return $(this.$el)
        },
        modal_id() {
            return `${this.instance_name}_integration`
        }
    },
    methods: {
        async get_namespaces() {
            const api_url = V.build_api_url('kubernetes', 'get_namespaces')
            const resp = await fetch(api_url,
                {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(this.body_data)
                })
            if (resp.ok) {
                this.namespaces = await resp.json()
            } else {
                console.warn('Couldn\'t fetch namespaces. Resp code: ', resp.status)
            }
            this.$nextTick(this.refresh_pickers)
            this.$nextTick(this.refresh_pickers)
        },
        clear() {
            Object.assign(this.$data, this.initialState())
            this.$nextTick(this.refresh_pickers)
        },
        load(stateData) {
            Object.assign(this.$data, stateData)
            this.$nextTick(this.refresh_pickers)
        },
        handleEdit(data) {
            const {description, is_default, id, settings} = data
            const namespaces = [settings.namespace]
            this.load({...settings, description, is_default, id, namespaces})
            this.modal.modal('show')
        },
        refresh_pickers() {
            $(this.$el).find('.selectpicker').selectpicker('render').selectpicker('refresh')
        },
        handleDelete(id) {
            this.load({id})
            this.delete()
        },
        create() {
            this.is_fetching = true
            fetch(this.apiPath + this.pluginName, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(this.body_data)
            }).then(response => {
                this.is_fetching = false
                if (response.ok) {
                    this.modal.modal('hide')
                    this.$emit('update', {...this.$data, section_name: this.section_name})

                } else {
                    this.handleError(response)
                }
            })
        },
        handleError(response) {
            try {
                response.json().then(
                    errorData => {
                        errorData.forEach(item => {
                            this.error = {[item.loc[0]]: item.msg}
                        })
                    }
                )
            } catch (e) {
                alertMain.add(e, 'danger-overlay')
            }
        },
        update() {
            this.is_fetching = true
            fetch(this.apiPath + this.id, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(this.body_data)
            }).then(response => {
                this.is_fetching = false
                if (response.ok) {
                    this.modal.modal('hide')
                    this.$emit('update', {...this.$data, section_name: this.section_name})

                } else {
                    this.handleError(response)
                }
            })
        },
        delete() {
            this.is_fetching = true
            fetch(this.apiPath + this.id, {
                method: 'DELETE',
            }).then(response => {
                this.is_fetching = false

                if (response.ok) {
                    this.$emit('update', {...this.$data, section_name: this.section_name})

                } else {
                    this.handleError(response)
                    alertMain.add(`
                        Deletion error. 
                        <button class="btn btn-primary" 
                            onclick="vueVm.registered_components.${this.instance_name}.modal.modal('show')"
                        >
                            Open modal
                        <button>
                    `)
                }
            })
        },

        initialState: () => ({
            modal_style: {'height': '100px', 'border': ''},
            k8s_token: '',
            namespace: "default",
            namespaces: ["default"],
            hostname: '',
            is_default: false,
            scaling_cluster: false,
            is_fetching: false,
            secure_connection: false,
            description: '',
            error: {},
            id: null,
            pluginName: 'kubernetes',
            api_base: '/api/v1/integrations/',
            status: integration_status.success,
        })
    }
}

register_component('KubernetesIntegration', KubernetesIntegration)
