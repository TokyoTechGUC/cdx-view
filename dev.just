dev_compose := "docker compose -f docker-compose.dev.yml --env-file .env.dev"

set positional-arguments := true

up *args:
    {{dev_compose}} up {{args}}

down *args:
    {{dev_compose}} down {{args}}

build *args:
    {{dev_compose}} build {{args}}

server *args='bash':
    {{dev_compose}} exec server-dev {{args}}

client *args='sh':
    {{dev_compose}} exec client-dev {{args}}

client-test *args:
    {{dev_compose}} exec client-dev npm test {{args}}

registry-test *args:
    {{dev_compose}} run --rm registry-dev pytest {{args}}

registry *args='bash':
    {{dev_compose}} run --rm registry-dev {{args}}

logs *args:
    {{dev_compose}} logs {{args}}

# -- Database Operations --

db-init:
    {{dev_compose}} run --rm registry-dev python register.py init

# --- Project commands ---

db-create-project *args:
    #!/usr/bin/env bash
    {{dev_compose}} run --rm registry-dev python register.py create-project "$@"

db-list-projects:
    {{dev_compose}} run --rm registry-dev python register.py list-projects

db-delete-project *args:
    #!/usr/bin/env bash
    {{dev_compose}} run --rm registry-dev python register.py delete-project "$@"

# --- Dataset commands ---

db-list-datasets *args:
    #!/usr/bin/env bash
    {{dev_compose}} run --rm registry-dev python register.py list-datasets "$@"

db-register-dataset *args:
    #!/usr/bin/env bash
    {{dev_compose}} run --rm registry-dev python register.py register-dataset "$@"

db-delete-dataset *args:
    #!/usr/bin/env bash
    {{dev_compose}} run --rm registry-dev python register.py delete-dataset "$@"

db-edit-dataset *args:
    #!/usr/bin/env bash
    {{dev_compose}} run --rm registry-dev python register.py edit-dataset "$@"
