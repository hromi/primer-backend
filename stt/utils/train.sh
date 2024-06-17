#!/bin/bash
#FINE-TUNES INDIVIDUAL MODELS FOR DIFFERENT PEOPLE/LANGUAGES COMBINATIONS, TRIGGERED by trigger_bot

#PHASE=("origin" "phase1")
SUBJECT=$1
LANGUAGE=$2
EPOCH=1
ORIGIN_MODEL=/data/checkpoints/$LANGUAGE
USER_DIR=/data/HMPL/$SUBJECT/$LANGUAGE
MODEL_DIR=/data/HMPL/$SUBJECT/$LANGUAGE/models
OLD_CHECKPOINT_DIR=$USER_DIR/checkpoints/last
LAST_CSV=$(ls -t $USER_DIR/learn/all*.csv |head -n1)
SESSION_ID=$(echo $LAST_CSV |grep -oP '(?<!/)\d+(?<=.)')
MODEL_DIR=/data/HMPL/$SUBJECT/$LANGUAGE/models/$SESSION_ID
NEW_CHECKPOINT_DIR=/data/HMPL/$SUBJECT/$LANGUAGE/checkpoints/$SESSION_ID

echo "$LAST_CSV SESSION_ID $SESSION_ID"
mkdir -p $MODEL_DIR
mkdir -p $NEW_CHECKPOINT_DIR

#source /data/deepspeech-train-jetson-venv/bin/activate

if [ -f "$OLD_CHECKPOINT_DIR/checkpoint" ]; then
	if [ "$OLD_CHECKPOINT_DIR/checkpoint" -nt "$LAST_CSV" ]; then
		echo "NO NEW DATA, EXITING"
		exit
	fi
	echo "OLD CHECKPOINT MODEL"
	LOAD_DIR=$OLD_CHECKPOINT_DIR
else
	echo "$OLD_CHECKPOINT_DIR not found, loading ORIGIN MODEL"
	if [[ $LANGUAGE == *"sk"*  || $LANGUAGE == *"cs"* ]]; then
		LOAD_DIR="/data/checkpoints/csk"
	else
		LOAD_DIR=$ORIGIN_MODEL
	fi
fi

[[ "$LANGUAGE" == "de" ]]  && CUDNN="--notrain_cudnn" || CUDNN="--train_cudnn"
#[[ "$LANGUAGE" == "sk" ]]  && AUT="--automatic_mixed_precision" || AUT=""
AUT=""
[[ "$LANGUAGE" == "sk" ]]  && LANGUAGE="csk"

#TRAINING PROCESS
echo training $SUBJECT $LANGUAGE ...
#echo python3 /data/DeepSpeech/DeepSpeech.py --n_hidden 2048 --learning_rate 0.0001 --alphabet_config_path /data/alphabets/deepspeech/$LANGUAGE/alphabet.txt --train_files $LAST_CSV --epochs $EPOCH --max_to_keep=25 --load_checkpoint_dir $LOAD_DIR --save_checkpoint_dir=$USER_CHECKPOINT_DIR --export_dir $USER_DIR --summary_dir=$USER_DIR/tensorboard/ --train_cudnn
echo python3.6 /data/DeepSpeech/DeepSpeech.py --max_to_keep 1 --n_hidden 2048 --learning_rate 0.0001 --alphabet_config_path /data/alphabets/deepspeech/$LANGUAGE/alphabet.txt --train_files $LAST_CSV --epochs $EPOCH --load_checkpoint_dir $LOAD_DIR --save_checkpoint_dir=$NEW_CHECKPOINT_DIR --export_dir $MODEL_DIR --summary_dir=$USER_DIR/tensorboard/ $CUDNN $AUT

#if ! python3.6 /data/DeepSpeech/DeepSpeech.py --max_to_keep 1 --n_hidden 2048 --learning_rate 0.0001 --alphabet_config_path /data/alphabets/deepspeech/$LANGUAGE/alphabet.txt --train_files $LAST_CSV --epochs $EPOCH --load_checkpoint_dir $LOAD_DIR --save_checkpoint_dir=$NEW_CHECKPOINT_DIR --export_dir $MODEL_DIR --summary_dir=$USER_DIR/tensorboard/ $CUDNN $AUT ; then
if python3.6 /data/DeepSpeech/DeepSpeech.py --max_to_keep 1 --n_hidden 2048 --learning_rate 0.0001 --alphabet_config_path /data/alphabets/deepspeech/$LANGUAGE/alphabet.txt --train_files $LAST_CSV --epochs $EPOCH --load_checkpoint_dir $LOAD_DIR --save_checkpoint_dir=$NEW_CHECKPOINT_DIR --export_dir $MODEL_DIR --summary_dir=$USER_DIR/tensorboard/ $CUDNN $AUT ; then

#create symslink to the new model to be used from now on
	echo "SYMLINKIN"
	rm $USER_DIR/output_graph.pb
	ln -s $MODEL_DIR/output_graph.pb $USER_DIR/output_graph.pb
	rm $OLD_CHECKPOINT_DIR
	ln -s $NEW_CHECKPOINT_DIR $OLD_CHECKPOINT_DIR

fi
#echo training is done!
