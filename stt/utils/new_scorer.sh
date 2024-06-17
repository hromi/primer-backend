#!/bin/bash
source /data/deepspeech-train-jetson-venv/bin/activate
mkdir /data/lms/$1
if [ -n "$3" ];then
	alpha=$3
else
	alpha=0.6
fi
echo "creating $2 scorer $1 with alpha $alpha" 
curl https://fibel.digital/$1/raw -o /data/lms/$1/$1.txt
python3 /data/DeepSpeech/data/lm/generate_lm.py --input_txt /data/lms/$1/$1.txt --output_dir /data/lms/$1 --top_k 500000 --kenlm_bins ./kenlm_bins --arpa_order 4 --max_arpa_memory "1%" --arpa_prune "0|0|1" --binary_a_bits 255 --binary_q_bits 8 --binary_type trie --discount_fallback
/data/utils/generate_scorer_package --lm /data/lms/$1/lm.binary --vocab /data/lms/$1/vocab-500000.txt  --checkpoint /data/alphabets/deepspeech/$2/ --package /data/scorers/$1.scorer --default_alpha $alpha --default_beta 1.1834137581510284
