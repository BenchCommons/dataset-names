#!/usr/bin/env bash
# Release do dataset (spec 006, R7; ADR 0014). Este script nunca publica release nem cria tag:
# publicar o rascunho é ato do dono do repositório.
#
#   tools/release.sh check RELEASE                 confere o nome da release (AAAA.MM[.N])
#   tools/release.sh fixture-cache CACHE           monta um cache de ensaio com as amostras de tests/fixtures
#   tools/release.sh fetch-cache RELEASE CACHE     baixa source-cache.tar.gz do rascunho RELEASE e o extrai em CACHE
#   tools/release.sh build RELEASE CACHE SAIDA     namescommons run --offline sobre CACHE e verificação da SAIDA
#   tools/release.sh verify SAIDA                  confere os arquivos e o SHA256SUMS da SAIDA
#   tools/release.sh upload RELEASE SAIDA          envia os assets ao rascunho RELEASE e remove dele o cache
set -euo pipefail

RAIZ=$(cd "$(dirname "$0")/.." && pwd)
CALVER='^[0-9]{4}\.(0[1-9]|1[0-2])(\.[1-9][0-9]*)?$'
CACHE_ASSET=source-cache.tar.gz
OBRIGATORIOS="manifest.json observations.parquet given_names.csv given_names.parquet family_names.csv
family_names.parquet by_country.zip DATA_LICENSE ATTRIBUTION.txt DATASET_CARD.md SHA256SUMS"

erro() {
    echo "release.sh: $*" >&2
    exit 1
}

conferir_release() {
    [[ "$1" =~ $CALVER ]] || erro "release '$1' fora do formato AAAA.MM[.N]"
}

absoluto() {
    mkdir -p "$1"
    (cd "$1" && pwd)
}

# Estado da release no GitHub: true (rascunho), false (publicada) ou ausente. Qualquer outro erro
# do gh (credencial, rede, limite de requisições) derruba o script com a mensagem real.
estado() {
    local saida
    if saida=$(gh release view "$1" --json isDraft --jq .isDraft 2>&1); then
        echo "$saida"
    elif [[ "$saida" == *"release not found"* ]]; then
        echo ausente
    else
        erro "falha ao consultar a release '$1' no GitHub: $saida"
    fi
}

# Nomes dos assets da release, um por linha; falha do gh derruba o script.
assets_da_release() {
    gh release view "$1" --json assets --jq '.assets[].name' || erro "falha ao listar os assets da release '$1'"
}

# Verdadeiro se a lista de nomes (um por linha) tem o asset do cache. Sem pipe nem grep -q:
# com pipefail, um SIGPIPE faria a busca falhar em silêncio.
tem_cache() {
    [[ $'\n'"$1"$'\n' == *$'\n'"$CACHE_ASSET"$'\n'* ]]
}

exigir_rascunho() {
    local e
    e=$(estado "$1") || exit 1
    case "$e" in
        true) ;;
        false) erro "a release '$1' já está publicada; releases são imutáveis, use uma release nova" ;;
        *) erro "nenhum rascunho de release '$1': crie um rascunho (draft) da release '$1' no GitHub e anexe $CACHE_ASSET (ADR 0014; procedimento no AGENTS.md)" ;;
    esac
}

verificar() {
    local saida=$1 nome listados existentes
    [ -d "$saida" ] || erro "diretório da release não encontrado: $saida"
    for nome in $OBRIGATORIOS; do
        [ -f "$saida/$nome" ] || erro "$saida: falta $nome"
    done
    listados=$(sed 's/^[0-9a-f]\{64\}  //' "$saida/SHA256SUMS" | LC_ALL=C sort)
    existentes=$(cd "$saida" && for nome in *; do
        [ -f "$nome" ] && [ "$nome" != SHA256SUMS ] && echo "$nome"
    done | LC_ALL=C sort)
    if [ "$listados" != "$existentes" ]; then
        erro "SHA256SUMS não cobre exatamente os arquivos de $saida: $(diff <(echo "$listados") <(echo "$existentes") | grep '^[<>]' | tr '\n' ' ')"
    fi
    if command -v sha256sum >/dev/null 2>&1; then
        (cd "$saida" && sha256sum -c SHA256SUMS) || erro "SHA256SUMS não confere em $saida"
    else
        (cd "$saida" && shasum -a 256 -c SHA256SUMS) || erro "SHA256SUMS não confere em $saida"
    fi
}

comando=${1:-}
[ $# -gt 0 ] && shift
case "$comando" in
    check)
        [ $# -eq 1 ] || erro "uso: release.sh check RELEASE"
        conferir_release "$1"
        ;;
    fixture-cache)
        [ $# -eq 1 ] || erro "uso: release.sh fixture-cache CACHE"
        cache=$(absoluto "$1")
        find "$RAIZ/tests/fixtures" -mindepth 1 -maxdepth 1 -type d ! -name exemplo -exec cp -R {} "$cache/" \;
        ;;
    fetch-cache)
        [ $# -eq 2 ] || erro "uso: release.sh fetch-cache RELEASE CACHE"
        conferir_release "$1"
        exigir_rascunho "$1"
        temporario=$(mktemp -d)
        trap 'rm -rf "$temporario"' EXIT
        gh release download "$1" --pattern "$CACHE_ASSET" --dir "$temporario" \
            || erro "o rascunho '$1' não tem o asset $CACHE_ASSET (ADR 0014)"
        [ -f "$temporario/$CACHE_ASSET" ] || erro "o rascunho '$1' não tem o asset $CACHE_ASSET (ADR 0014)"
        cache=$(absoluto "$2")
        tar -xzf "$temporario/$CACHE_ASSET" -C "$cache"
        ;;
    build)
        [ $# -eq 3 ] || erro "uso: release.sh build RELEASE CACHE SAIDA"
        conferir_release "$1"
        [ -d "$2" ] || erro "cache não encontrado: $2"
        cache=$(cd "$2" && pwd)
        mkdir -p "$(dirname "$3")"
        saida="$(cd "$(dirname "$3")" && pwd)/$(basename "$3")"
        (cd "$RAIZ" && uv run namescommons run --offline --cache "$cache" --out "$saida" --release "$1" \
            --sources "$RAIZ/sources.yaml" --data-license "$RAIZ/DATA_LICENSE")
        verificar "$saida"
        ;;
    verify)
        [ $# -eq 1 ] || erro "uso: release.sh verify SAIDA"
        verificar "$1"
        ;;
    upload)
        [ $# -eq 2 ] || erro "uso: release.sh upload RELEASE SAIDA"
        conferir_release "$1"
        verificar "$2"
        exigir_rascunho "$1"
        assets=()
        for arquivo in "$2"/*; do
            [ -f "$arquivo" ] && assets+=("$arquivo")
        done
        # Sem sobrescrever: um asset que já existe no rascunho faz o envio falhar.
        gh release upload "$1" "${assets[@]}"
        nomes=$(assets_da_release "$1") || exit 1
        if tem_cache "$nomes"; then
            gh release delete-asset "$1" "$CACHE_ASSET" --yes
            nomes=$(assets_da_release "$1") || exit 1
            if tem_cache "$nomes"; then
                erro "$CACHE_ASSET continua no rascunho '$1' depois da remoção; apague-o antes de publicar"
            fi
        fi
        echo "Assets enviados ao rascunho '$1'. Revise e publique pelo GitHub; este script não publica."
        ;;
    *)
        erro "uso: release.sh {check|fixture-cache|fetch-cache|build|verify|upload} ..."
        ;;
esac
