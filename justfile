prod_compose := "docker compose -f docker-compose.yml --env-file .env"

set positional-arguments := true

mod dev

up *args:
    {{prod_compose}} up {{args}}

down *args:
    {{prod_compose}} down {{args}}

build *args:
    {{prod_compose}} build {{args}}

logs *args:
    {{prod_compose}} logs {{args}}

# -- Database Operations --

db-init:
    {{prod_compose}} run --rm registry python register.py init

# --- Project commands ---

db-create-project *args:
    #!/usr/bin/env bash
    {{prod_compose}} run --rm registry python register.py create-project "$@"

db-list-projects:
    {{prod_compose}} run --rm registry python register.py list-projects

db-delete-project *args:
    #!/usr/bin/env bash
    {{prod_compose}} run --rm registry python register.py delete-project "$@"

# --- Dataset commands ---

db-list-datasets *args:
    #!/usr/bin/env bash
    {{prod_compose}} run --rm registry python register.py list-datasets "$@"

db-register-dataset *args:
    #!/usr/bin/env bash
    {{prod_compose}} run --rm registry python register.py register-dataset "$@"

db-delete-dataset *args:
    #!/usr/bin/env bash
    {{prod_compose}} run --rm registry python register.py delete-dataset "$@"

db-edit-dataset *args:
    #!/usr/bin/env bash
    {{prod_compose}} run --rm registry python register.py edit-dataset "$@"
