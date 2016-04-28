import logging
from intent.utils.token import tag_tokenizer, tokenize_string

TAGLOG = logging.getLogger("TEST_TAGGERS")
#logging.basicConfig(level=logging.DEBUG)


from argparse import ArgumentParser
from tempfile import NamedTemporaryFile
import sys
from intent.eval.pos_eval import slashtags_eval
from intent.interfaces.stanford_tagger import train_postagger, StanfordPOSTagger, test_postagger
from intent.utils.argutils import existsfile

def remove_tags(source_path, target_path):
    source_f = open(source_path, 'r', encoding='utf-8')
    target_f = open(target_path, 'w', encoding='utf-8')

    for line in source_f:
        tokens = tokenize_string(line, tokenizer=tag_tokenizer)
        target_f.write(tokens.text()+'\n')

    source_f.close()
    target_f.close()




if __name__ == '__main__':
    p = ArgumentParser()
    p.add_argument('--train', help='Training file.', type=existsfile)
    p.add_argument('--tagger', help='Path to a pre-trained tagger.', type=existsfile)
    p.add_argument('--test', help='File to evaluate against.', required=True, type=existsfile)
    p.add_argument('--delimiter', help='Token to separate tags from words (default "/")', default='/')
    p.add_argument('--output', help='Optionally, save the tagger output to this path.')

    args = p.parse_args()

    if not (args.train or args.tagger):
        sys.stderr.write("Either a training file or a pre-trained tagger is required.")
        p.print_help()
        sys.exit(11)

    if args.train and args.tagger:
        sys.stderr.write("WARNING: Both a training file and a tagger were specified. The tagger will take precedence.")

    # =============================================================================
    # First, train the tagger.
    # =============================================================================

    if args.train and not args.tagger:
        print('Training tagger from "{}"'.format(args.train))
        tagger_file = NamedTemporaryFile('w')
        tagger = train_postagger(args.train, tagger_file.name)
        print("Tagger training complete.")
        tagger_path = tagger_file.name
    else:
        print('Loading tagger from "{}"'.format(args.tagger))
        tagger_path = args.tagger

    # =============================================================================
    # Next, strip the tags from the test file into a temporary file.
    # =============================================================================
    raw_tmp = NamedTemporaryFile()

    remove_tags(args.test, raw_tmp.name)
    # =============================================================================
    # Figure out if we want to save the output path
    # =============================================================================
    if args.output:
        outpath = args.output
    else:
        output_file = NamedTemporaryFile('w', encoding='utf-8')
        outpath = output_file.name

    print('Running tagger on "{}"'.format(args.test))
    test_postagger(raw_tmp.name, tagger_path, outpath)

    print("RESULTS ON SENTENCES OF ALL LENGTHS")
    slashtags_eval(args.test, outpath, args.delimiter, details=True, matrix=False, length_limit=None)

    print("RESULTS ON SENTENCES OF <=10")
    slashtags_eval(args.test, outpath, args.delimiter, details=True, matrix=False, length_limit=10)

